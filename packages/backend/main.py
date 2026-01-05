from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sys
import os
import sqlite3
import json
import importlib.util
from typing import Any, TYPE_CHECKING

from sudachipy import tokenizer
from sudachipy import dictionary

# Importing tdmelodic internals from installed package
try:
    from tdmelodic.nn.inference import InferAccent
    from tdmelodic.nn.loader.data_loader import (
        _convert_parsed_surface_to_codes,
        _convert_yomi_to_codes,
        normalize_jpn,
        UniDic,
        kana2roman,
    )
    from tdmelodic.nn.lang.japanese.kana.mora_sep import sep_katakana2mora
    from tdmelodic.nn.lang.japanese.kana.kanamap.kanamap_normal import roman_map
    from tdmelodic.nn.lang.category.symbol_map import char_symbol_to_numeric
    from tdmelodic.nn.lang.japanese.accent.accent_alignment import (
        accent_map,
        accent_align,
    )
    from chainer.dataset.convert import concat_examples
except ImportError as e:
    print(f"Error importing tdmelodic: {e}")
    sys.exit(1)

if TYPE_CHECKING:

    class OriginalConverter:
        def encode_sy(self, surface: str, yomi: str) -> Any: ...
        def add_batch_dim(self, s: Any, y: Any) -> Any: ...
        def infer(self, s: Any, l: Any) -> Any: ...

else:
    OriginalConverter = object

# Dynamically load Converter from vendor submodule
# because it is missing in the installed package.
# Also inject tdmelodic.util which is missing in installed package but needed by convert.py
try:
    vendor_root = os.path.join(
        os.path.dirname(__file__), "vendor", "tdmelodic", "tdmelodic"
    )

    # Packet: tdmelodic.util
    util_dir = os.path.join(vendor_root, "util")
    util_init = os.path.join(util_dir, "__init__.py")
    spec_util = importlib.util.spec_from_file_location("tdmelodic.util", util_init)
    if spec_util and spec_util.loader:
        module_util = importlib.util.module_from_spec(spec_util)
        # Important: Set __path__ so that submodules (like dic_index_map) can be found
        module_util.__path__ = [util_dir]
        sys.modules["tdmelodic.util"] = module_util
        spec_util.loader.exec_module(module_util)

    # Convert Module
    convert_path = os.path.join(vendor_root, "nn", "convert.py")
    spec = importlib.util.spec_from_file_location("tdmelodic.nn.convert", convert_path)
    if spec and spec.loader:
        convert_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(convert_module)
        if not TYPE_CHECKING:
            OriginalConverter = convert_module.Converter
except Exception as e:
    print(f"Error loading tdmelodic submodule: {e}")
    # Print traceback to help debugging
    import traceback

    traceback.print_exc()
    sys.exit(1)

app = FastAPI()

# Configure CORS
from fastapi.middleware.cors import CORSMiddleware

# In production, this should be set to the actual frontend domain
# For now, we allow all origins to make development and deployment easier
origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AnalyzeRequest(BaseModel):
    text: str


class AnalyzeResponse(BaseModel):
    text: str
    reading: str
    accent_pattern: list[int]
    accent_code: str  # Visualization string (e.g. "ハ[シ")


class CustomConverter(OriginalConverter):
    def __init__(self):
        # Do not call super().__init__() because it crashes trying to find default mecabrc
        # Instead, we manually initialize what the parent would have, but with CORRECT arguments.
        self.model = InferAccent()

        # Override UniDic to use OUR custom mecabrc
        # We assume 'unidic' package is installed in the env.
        import unidic

        self.unidic = UniDic(unidic_path=unidic.DICDIR, mecabrc_path="mecabrc")

        # Initialize Sudachi for robust readings
        self.sudachi_dict = dictionary.Dictionary(dict="small")
        self.mode = tokenizer.Tokenizer.SplitMode.C

    def generate_visualization(self, reading: str, pattern: list[int]) -> str:
        morae = sep_katakana2mora(reading)
        display_str = ""
        for i, (m, p) in enumerate(zip(morae, pattern)):
            prefix = ""
            suffix = ""
            if p == 2:  # High
                if i == 0 or pattern[i - 1] == 1:
                    if i > 0:
                        prefix = "["
            if p == 2:
                if i + 1 < len(pattern) and pattern[i + 1] == 1:
                    suffix = "]"
            display_str += prefix + m + suffix
        return display_str

    def convert(self, text: str):
        # 1. Normalize (Standard step, though encode_sy also does some)
        surface = normalize_jpn(text)

        # 2. Sudachi Analysis for Yomi
        # Create tokenizer per request to ensure thread safety (avoids RuntimeError: Already borrowed)
        tokenizer_instance = self.sudachi_dict.create()
        tokens = tokenizer_instance.tokenize(text, self.mode)
        yomi = "".join([m.reading_form() for m in tokens])

        # 3. UniDic Analysis & Dictionary Accent Check
        # We need to manually check for the dictionary kernel because encode_sy doesn't return it.
        tmp = self.unidic.get_n_best(surface, yomi)
        if not tmp:
            raise HTTPException(status_code=400, detail="Could not analyze text")

        lst_mecab_parsed, rank, ld = tmp
        mecab_parsed = lst_mecab_parsed[0]

        acc_kernel_str = None
        if len(mecab_parsed) == 1:
            acc_kernel_str = mecab_parsed[0].get("acc")
            # Handle multiple accent types (e.g. "1,2") by taking the first one
            if acc_kernel_str and "," in acc_kernel_str:
                acc_kernel_str = acc_kernel_str.split(",")[0]

        preds = []
        current_level = 1  # Default initialization

        if acc_kernel_str and acc_kernel_str.isdigit():
            # Dictionary Fast Path
            kernel = int(acc_kernel_str)
            roman = kana2roman(yomi)
            acc_str_full = accent_align(roman, str(kernel))
            acc_str = acc_str_full[0::2]
            preds = [1 if c == "L" else 2 if c == "H" else 0 for c in acc_str]
            if preds:
                current_level = preds[-1]
        else:
            # ML Fallback using Parent Logic
            # We use parent methods to ensure consistency with library implementation
            if hasattr(self, "encode_sy"):  # Runtime check or trust the flow
                s_np, y_np = self.encode_sy(surface, yomi)
                s_np, y_np = self.add_batch_dim(s_np, y_np)
                codes = self.infer(s_np, y_np).tolist()[0]

                # Convert valid tdmelodic codes (0=], 1=, 2=[) to Pitch Levels (1=L, 2=H)
                current_level = 2 if (len(codes) > 0 and codes[0] == 0) else 1
                preds = []
                for c in codes:
                    preds.append(current_level)
                    if c == 2:  # Rise -> Next H
                        current_level = 2
                    elif c == 0:  # Fall -> Next L
                        current_level = 1
                    # c==1 -> Next same as current
            else:
                # Should not happen if initialization worked
                raise HTTPException(
                    status_code=500, detail="Model not initialized correctly"
                )

        # 6. Post-process trimming
        morae = sep_katakana2mora(yomi)
        preds = preds[: len(morae)]
        if len(preds) < len(morae):
            preds += [current_level] * (len(morae) - len(preds))

        # 7. Visualization
        display_str = self.generate_visualization(yomi, preds)

        return {
            "text": text,
            "reading": yomi,
            "accent_pattern": preds,
            "accent_code": display_str,
        }


converter = CustomConverter()


# DB Setup
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "candidates.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/")
def read_root():
    return {"status": "ok", "service": "tdmelodic-api"}


@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    return converter.convert(request.text)


@app.get("/api/target-word", response_model=AnalyzeResponse)
def get_target_word(min_mora: int = 2, max_mora: int = 8):
    conn = get_db_connection()
    try:
        # Get random word within mora range
        # SQLite ORDER BY RANDOM() is okay for small datasets
        row = conn.execute(
            "SELECT * FROM candidates WHERE mora_count >= ? AND mora_count <= ? ORDER BY RANDOM() LIMIT 1",
            (min_mora, max_mora),
        ).fetchone()

        if not row:
            raise HTTPException(
                status_code=404, detail="No words found for this difficulty"
            )

        accent_pattern = json.loads(row["accent_pattern"])
        accent_code = converter.generate_visualization(row["reading"], accent_pattern)

        return {
            "text": row["text"],
            "reading": row["reading"],
            "accent_pattern": accent_pattern,
            "accent_code": accent_code,
        }
    finally:
        conn.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
