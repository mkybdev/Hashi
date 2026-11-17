"""語末の外側を含めず、拍ごとの高低列を比較する。1=低、2=高。"""

def from_kernel(mora_count, kernel):
    return [2 if (i == 0 if kernel == 1 else i > 0 and (kernel == 0 or i < kernel)) else 1
            for i in range(mora_count)]


def from_codes(codes, mora_count):
    # tdmelodicは最初の拍の後の通常の上昇を省略するので復元する。
    if mora_count < 1 or len(codes) < mora_count or any(c not in (0, 1, 2) for c in codes[:mora_count]):
        raise ValueError('推定された高低列の長さまたはコードが不正です。')
    level = 2 if codes[0] == 0 else 1
    pattern = [level]
    for i, code in enumerate(codes[:mora_count - 1]):
        if code == 0:
            level = 1
        elif code == 2 or i == 0:
            level = 2
        pattern.append(level)
    return pattern


def matching_pattern(a, b):
    other = {tuple(p) for p in b['pitch_patterns']}
    return next((p for p in a['pitch_patterns'] if tuple(p) in other), None)
