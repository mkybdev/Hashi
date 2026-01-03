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

# Initialize Sudachi
tokenizer_obj = dictionary.Dictionary(dict="small").create()
mode = tokenizer.Tokenizer.SplitMode.C

# Initialize tdmelodic model
# InferAccent handles model download if missing
accent_model = InferAccent()

# Initialize UniDic wrapper from tdmelodic if needed
# We need to point to the installed unidic
import unidic
unidic_wrapper = UniDic(unidic_path=unidic.DICDIR)

@app.get("/")
def read_root():
    return {"status": "ok", "service": "tdmelodic-api"}

@app.post("/api/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest):
    text = request.text
    
    # 1. Morphological Analysis with Sudachi to get Surface & Reading (Yomi)
    # tdmelodic expects a single word or a phrase that aligns with UniDic entries ideally,
    # but here we might accept a full sentence? 
    # The requirement says "Input a Japanese word". So we assume single word usage primarily.
    # If multiple words, we might need to loop. For now, treat as one block or first token?
    # Let's process the whole text as one if possible, or split.
    # tdmelodic is designed for dictionary entry generation, so it works on "words".
    # We will try to process each morpheme? No, the game is about "Word" accent.
    # So we assume input is a word.
    
    # Get Yomi from Sudachi
    tokens = tokenizer_obj.tokenize(text, mode)
    # Concatenate readings if multiple tokens?
    # But tdmelodic needs MeCab-like parsing features (POS, etc) for its Neural Net input.
    # UniDic wrapper in tdmelodic does `get_n_best`.
    
    # Let's try to use UniDic wrapper directly on the text if it supports it.
    # unidic.get_n_best(surface, yomi)
    
    # We use Sudachi to get the Yomi first, because UniDic might not know the word if it's new,
    # but tdmelodic is robust?
    # Actually, if we provide Yomi, tdmelodic can infer.
    
    yomi = "".join([m.reading_form() for m in tokens])
    # Convert to Katakana just in case Sudachi returns something else (it returns Katakana usually)
    
    # Normalize
    surface_ = normalize_jpn(text)
    
    # Use tdmelodic's UniDic wrapper to get features
    # If yomi is provided, it constrains the search or is used as is?
    # get_n_best(surface, yomi) returns (lst_mecab_parsed, rank, ld)
    tmp = unidic_wrapper.get_n_best(surface_, yomi)
    if not tmp:
        # Fallback?
        raise HTTPException(status_code=400, detail="Could not analyze text")
        
    lst_mecab_parsed, rank, ld = tmp
    # We pick the best rank (0)
    mecab_parsed = lst_mecab_parsed[0]
    
    # Convert to codes
    # codes : v_code, c_code, accent_code, pos_code, conc_code, gosh_code
    S_vow, S_con, S_acc, S_pos, S_acccon, S_gosh = _convert_parsed_surface_to_codes(mecab_parsed)
    Y_vow, Y_con = _convert_yomi_to_codes(yomi)

    # Prepare batch (size 1) - logic adapted from data_loader.py
    # join
    S_vow    = ''.join([s + ' ' for s in S_vow])
    S_con    = ''.join([s + ' ' for s in S_con])
    S_acc    = ''.join([s       for s in S_acc])
    S_pos    = ''.join([s + ' ' for s in S_pos])
    S_acccon = ''.join([s + ' ' for s in S_acccon])
    S_gosh   = ''.join([s + ' ' for s in S_gosh])
    Y_vow    = ''.join([s + ' ' for s in Y_vow])
    Y_con    = ''.join([s + ' ' for s in Y_con])
    
    # Mappings
    from tdmelodic.nn.lang.japanese.kana.kanamap.kanamap_normal import roman_map
    from tdmelodic.nn.lang.category.symbol_map import (
        char_symbol_to_numeric, 
        numeric_to_char_symbol
    )
    from tdmelodic.nn.lang.japanese.accent.accent_alignment import accent_map
    
    # We need to handle padding if we were batching, but for single item we just need Arrays.
    # Actually `concat_examples` in `convert_dic.py` pads 0.
    # Here we have 1 item.
    
    def to_np(seq, mapping, dtype=np.int32):
        return np.array([mapping[c] for c in seq], dtype)
        
    S_vow_np = to_np(S_vow, roman_map)
    S_con_np = to_np(S_con, roman_map)
    S_acc_np = to_np(S_acc, accent_map)
    S_pos_np = to_np(S_pos, char_symbol_to_numeric)
    S_acccon_np = to_np(S_acccon, char_symbol_to_numeric)
    S_gosh_np = to_np(S_gosh, char_symbol_to_numeric)
    
    Y_vow_np = to_np(Y_vow, roman_map)
    Y_con_np = to_np(Y_con, roman_map)
    
    # X_s = S_vow_np, S_con_np, S_pos_np, S_acc_np, S_acccon_np, S_gosh_np
    # X_y = Y_vow_np, Y_con_np
    
    # Need to add batch dimension?
    # The network likely expects batch dimension.
    # chainer.dataset.convert.concat_examples(batch) creates batch dim.
    
    # Let's import concat_examples
    from chainer.dataset.convert import concat_examples
    
    batch = [(S_vow_np, S_con_np, S_pos_np, S_acc_np, S_acccon_np, S_gosh_np, Y_vow_np, Y_con_np)]
    # We need a dummy 'y' (accent ground truth) for the batch if using the same structure as convert_dic?
    # In convert_dic.py: batch = [a for a, b in batch_] -> (X..., y)
    # And it splits X and y.
    # Here let's just create the tuple.
    
    batch_item = (S_vow_np, S_con_np, S_pos_np, S_acc_np, S_acccon_np, S_gosh_np, Y_vow_np, Y_con_np)
    # The batch function expects list of samples.
    # Samples are tuples.
    
    batch_out = concat_examples([batch_item], device=-1, padding=0)
    # output is a tuple of arrays, each has shape (1, ...)
    
    X_s = batch_out[:-2]
    X_y = batch_out[-2:]
    
    y_dummy_GT = (X_y[0] * 0) # dummy
    
    # Infer
    a_est = accent_model.infer(X_s, X_y, y_dummy_GT)
    # a_est is numpy array (1, L)
    
    preds = a_est[0].tolist()
    # Trim to length of yomi
    preds = preds[:len(yomi)]
    
    # Create visualization
    # 0: Low, 1: High?
    # Actually tdmelodic output mapping might be different.
    # In convert_dic.py:
    # up_symbol if a_ == 2 else down_symbol if a_ == 0 else ""
    # This suggests 3 classes? Or just boundaries?
    # a_est values: 0, 1, 2?
    # If 0: "]", 1: "", 2: "[" ?
    # Let's verify mapping.
    
    # sep_katakana2mora returns morae list.
    morae = sep_katakana2mora(yomi)
    
    display_str = ""
    for m, p in zip(morae, preds):
        prefix = "[" if p == 2 else ""
        suffix = "]" if p == 0 else ""
        display_str += prefix + m + suffix
        
    return {
        "text": text,
        "reading": yomi,
        "accent_pattern": preds,
        "accent_code": display_str
    }
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
