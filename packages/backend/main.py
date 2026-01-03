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
unidic_wrapper = UniDic(unidic_path=unidic.DICDIR, mecabrc_path="mecabrc")

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
    
    print(f"DEBUG: Text={text}")
    if len(mecab_parsed) > 0:
        print(f"DEBUG: Mecab Acc={mecab_parsed[0].get('acc')}, Concat={mecab_parsed[0].get('concat')}")
    print(f"DEBUG: S_acc={S_acc}")
    
    # Mappings
    from tdmelodic.nn.lang.japanese.kana.kanamap.kanamap_normal import roman_map
    from tdmelodic.nn.lang.japanese.accent.accent_alignment import accent_align
    
    # Check if we have a valid accent kernel from dictionary
    acc_kernel_str = mecab_parsed[0].get('acc')
    preds = []
    
    # Try to use dictionary accent first
    if acc_kernel_str and acc_kernel_str.isdigit():
        kernel = int(acc_kernel_str)
        # Convert yomi to roman for accent_align (it expects 1 mora = 2 chars roughly? No, accent_align doc says 'roman')
        # Actually accent_align expects roman length.
        # But we can simpler logic?
        # accent_align implementation:
        # Input: roman (string), a_kernel (int).
        # It calculates n_morae = len(roman) // 2.
        # So we need romanized yomi.
        
        # tdmelodic provides kana2roman
        roman = kana2roman(yomi)
        # normalize roman to ensure 2 chars per mora? kana2roman usually does.
        
        # accent_align returns string like "LLHHLL..." (r=2)
        acc_str_full = accent_align(roman, str(kernel))
        
        # Subsample to get 1 char per mora. Stride 2.
        # acc_str_full corresponds to roman (2 chars per mora).
        # So we take every 2nd char?
        # accent_align uses r=2. 'L'*r. So "LL".
        # We just need one of them.
        acc_str = acc_str_full[0::2]
        
        # Map L->1, H->2
        preds = [1 if c == 'L' else 2 if c == 'H' else 0 for c in acc_str]
        
        # Limit to morae length
        morae = sep_katakana2mora(yomi)
        if len(preds) > len(morae):
             preds = preds[:len(morae)]
        elif len(preds) < len(morae):
             # padding?
             preds += [1] * (len(morae) - len(preds))

    else:
        # Fallback to ML model
        
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
        
        # Import concat_examples
        from chainer.dataset.convert import concat_examples
        
        batch_item = (S_vow_np, S_con_np, S_pos_np, S_acc_np, S_acccon_np, S_gosh_np, Y_vow_np, Y_con_np)
        batch_out = concat_examples([batch_item], device=-1, padding=0)
        
        X_s = batch_out[:-2]
        X_y = batch_out[-2:]
        y_dummy_GT = (X_y[0] * 0) 
        
        # Infer
        a_est = accent_model.infer(X_s, X_y, y_dummy_GT)
        preds = a_est[0].tolist()
        # Trim to length of yomi
        preds = preds[:len(yomi)]
    
    # Create visualization
    morae = sep_katakana2mora(yomi)
    
    display_str = ""
    # With 1(L) and 2(H).
    # H-L transition is falling kernel.
    # L-H transition?
    # Downstep symbol "]" usually placed after the last High mora before a Low.
    # Upstep symbol "[" usually placed before the first High mora.
    
    # Standard notation:
    # Heiban (L H H ...): [ L H H ...
    # Atamadaka (H L ...):  H ] L ...
    # Nakadaka (L H ... H L): [ L H ... H ] L
    
    # My simple viz code using 2(H) and 1(L):
    # If change L->H: insert "[" ?
    # If change H->L: insert "]" ?
    
    # Let's iterate.
    # Logic:
    # If current is H and previous was L (or start): could be start of high.
    # If current is L and previous was H: end of high.
    
    # But wait, original code was:
    # prefix = "[" if p == 2 else ""
    # suffix = "]" if p == 0 else ""
    # This was assuming preds had specifically "Up/Down" codes (2/0).
    # BUT accent_map for ML output might be H=2, L=1.
    # If I changed preds to be H=2, L=1, I must update viz code.
    
    # Let's update viz code to work with L/H sequence.
    
    last_p = 1 # Assume start is Low-ish or handle first mora specially?
    # Actually, first mora:
    # If H (Atamadaka): Starts H.
    # If L (Others): Starts L.
    
    # Refined viz:
    # We want [ before first H (if not first mora?)
    # We want ] after last H (if followed by L).
    
    display_str = ""
    for i, (m, p) in enumerate(zip(morae, preds)):
        prefix = ""
        suffix = ""
        
        # Check start of High
        if p == 2:
             if i == 0:
                 pass # Start high, no bracket usually? Or maybe [ at start? 
                 # Usually Atamadaka is just "Hashi" with line on top of Ha.
                 # Text viz: "ハ[シ" ? No.
                 # "箸" (H-L): H ] L.  "ハ]シ"
                 # "橋" (L-H): L [ H.  "ハ[シ"
             else:
                 prev = preds[i-1]
                 if prev == 1: # L -> H
                     prefix = "["
        
        # Check end of High (Fall)
        if p == 2:
            # Look ahead?
            if i + 1 < len(preds):
                next_p = preds[i+1]
                if next_p == 1: # H -> L
                    suffix = "]"
            else:
                # End of word.
                # If Odaka (Hashi bridge), it falls AFTER word (particle).
                # But within word, it stays H?
                pass
        elif p == 1:
            pass # Low
            
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
