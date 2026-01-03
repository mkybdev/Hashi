from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sys
import os
import numpy as np

# Adjust path if needed to make sure imports work
# In some environments, site-packages might not be in path correctly if running via uvicorn without activation,
# but usually it's fine if running via `venv/bin/uvicorn`.

from sudachipy import tokenizer
from sudachipy import dictionary

# Importing tdmelodic internals
try:
    from tdmelodic.nn.inference import InferAccent
    from tdmelodic.nn.loader.data_loader import (
        _convert_parsed_surface_to_codes,
        _convert_yomi_to_codes,
        normalize_jpn,
        UniDic,
        kana2roman
    )
    from tdmelodic.nn.lang.japanese.kana.mora_sep import sep_katakana2mora
except ImportError as e:
    print(f"Error importing tdmelodic: {e}")
    sys.exit(1)

app = FastAPI()

class AnalyzeRequest(BaseModel):
    text: str

class AnalyzeResponse(BaseModel):
    text: str
    reading: str
    accent_pattern: list[int]
    accent_code: str # Visualization string (e.g. "ハ[シ")

# ... previous lines ...
import jaconv
import unidic
from tdmelodic.nn.lang.japanese.kana.kanamap.kanamap_normal import roman_map
from tdmelodic.nn.lang.category.symbol_map import char_symbol_to_numeric
from tdmelodic.nn.lang.japanese.accent.accent_alignment import accent_map, accent_align
from chainer.dataset.convert import concat_examples

class Converter(object):
    def __init__(self):
        # Initialize Sudachi
        self.tokenizer_obj = dictionary.Dictionary(dict="small").create()
        self.mode = tokenizer.Tokenizer.SplitMode.C
        
        self.model = InferAccent()
        self.unidic = UniDic(unidic_path=unidic.DICDIR, mecabrc_path="mecabrc")

    def convert(self, text: str):
        # 1. Normalize
        surface = normalize_jpn(text)
        
        # 2. Sudachi Analysis (to get robust reading)
        tokens = self.tokenizer_obj.tokenize(text, self.mode)
        yomi = "".join([m.reading_form() for m in tokens])
        
        # 3. UniDic Analysis
        tmp = self.unidic.get_n_best(surface, yomi)
        if not tmp:
             raise HTTPException(status_code=400, detail="Could not analyze text")
        
        lst_mecab_parsed, rank, ld = tmp
        mecab_parsed = lst_mecab_parsed[0]
        
        # 4. Dictionary Accent Check (Our verified improvement)
        # mecab_parsed is a list of tokens.
        # We only use the direct dictionary accent if it's a single token word (like Hashi).
        # For compound words, accent modification rules apply, so we trust the ML model (or we'd need complex rules).
        acc_kernel_str = None
        if len(mecab_parsed) == 1:
            acc_kernel_str = mecab_parsed[0].get('acc')
            
        preds = []
        used_dictionary = False
        
        if acc_kernel_str and acc_kernel_str.isdigit():
            kernel = int(acc_kernel_str)
            roman = kana2roman(yomi)
            acc_str_full = accent_align(roman, str(kernel))
            acc_str = acc_str_full[0::2]
            preds = [1 if c == 'L' else 2 if c == 'H' else 0 for c in acc_str]
            used_dictionary = True
        else:
             # 5. ML Model Inference (as backup)
             S_vow, S_con, S_acc, S_pos, S_acccon, S_gosh = _convert_parsed_surface_to_codes(mecab_parsed)
             Y_vow, Y_con = _convert_yomi_to_codes(yomi)
             
             # Conversions to NP
             def to_np(seq, mapping, dtype=np.int32):
                return np.array([mapping[c] for c in seq], dtype)
             
             S_vow_np = to_np(''.join([s + ' ' for s in S_vow]), roman_map)
             S_con_np = to_np(''.join([s + ' ' for s in S_con]), roman_map)
             S_acc_np = to_np(''.join(S_acc), accent_map) # S_acc is list of chars? No, _convert returns list. join it?
             # _convert_parsed_surface_to_codes returns lists of strings.
             # S_acc is ['-', 'D', ...].
             # We need to join them?
             # ' '.join? No. accent_map keys are single chars usually?
             # accent_map keys: '.', 'L', 'H', '?', '-', 'D', 'U'.
             # S_acc elements are these chars.
             # So join '' is correct.
             
             S_pos_np = to_np(''.join([s + ' ' for s in S_pos]), char_symbol_to_numeric)
             S_acccon_np = to_np(''.join([s + ' ' for s in S_acccon]), char_symbol_to_numeric)
             S_gosh_np = to_np(''.join([s + ' ' for s in S_gosh]), char_symbol_to_numeric)
             
             Y_vow_np = to_np(''.join([s + ' ' for s in Y_vow]), roman_map)
             Y_con_np = to_np(''.join([s + ' ' for s in Y_con]), roman_map)
             
             batch_item = (S_vow_np, S_con_np, S_pos_np, S_acc_np, S_acccon_np, S_gosh_np, Y_vow_np, Y_con_np)
             batch_out = concat_examples([batch_item], device=-1, padding=0)
             
             X_s = batch_out[:-2]
             X_y = batch_out[-2:]
             y_dummy_GT = (X_y[0] * 0) 
             
             a_est = self.model.infer(X_s, X_y, y_dummy_GT)
             preds = a_est[0].tolist()
        
        # 6. Post-process trimming
        morae = sep_katakana2mora(yomi)
        preds = preds[:len(morae)]
        if len(preds) < len(morae):
             preds += [1] * (len(morae) - len(preds))
             
        # 7. Visualization
        display_str = ""
        for i, (m, p) in enumerate(zip(morae, preds)):
            prefix = ""
            suffix = ""
            if p == 2: # High
                if i == 0 or preds[i-1] == 1:
                     # Start of High:
                     # If first mora is High: Atamadaka (H L ...). No "[" typically?
                     # Standard: Starts Low -> High means "[".
                     # "Hashi" (Bridge) L-H: Ha [ shi.
                     # "Hashi" (Chopsticks) H-L: Ha ] shi.
                     if i > 0: prefix = "["
            if p == 2:
                if i + 1 < len(preds) and preds[i+1] == 1:
                    suffix = "]"
            display_str += prefix + m + suffix
            
        return {
            "text": text,
            "reading": yomi,
            "accent_pattern": preds,
            "accent_code": display_str
        }

converter = Converter()

@app.get("/")
def read_root():
    return {"status": "ok", "service": "tdmelodic-api"}

@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    return converter.convert(request.text)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
