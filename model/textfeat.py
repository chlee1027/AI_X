"""글자 특징과 복원(정규화). 규칙은 유니코드 표준(NFKC, 문자 이름)과 한글 자모 조합 규칙에서 정했다(데이터를 보고 정하지 않음).

restore(s): NFKC -> 보이지 않는 문자(Cf, 소프트 하이픈) 제거 -> 라틴 닮은 문자(키릴·그리스·작은 대문자·수정자 글자) 를
            라틴으로 -> 호환·조합 자모를 음절로 묶기.
stats(s): 유니코드 구역별 글자 수 비율 등 수치 특징.
"""
import re
import unicodedata

# 키릴·그리스 글자 중 라틴과 모양이 같은 것(Unicode confusables 의 대표 짝)
CONF = str.maketrans({
    "а": "a", "в": "b", "е": "e", "к": "k", "м": "m", "н": "h", "о": "o", "р": "p", "с": "c", "т": "t", "у": "y",
    "х": "x", "і": "i", "ј": "j", "ѕ": "s", "ԁ": "d", "ԛ": "q", "ԝ": "w", "ӏ": "l", "ь": "b", "п": "n", "г": "r",
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P", "С": "C", "Т": "T", "Х": "X",
    "І": "I", "Ј": "J", "Ѕ": "S", "У": "Y", "Ь": "b",
    "α": "a", "β": "b", "ε": "e", "ι": "i", "κ": "k", "ν": "v", "ο": "o", "ρ": "p", "τ": "t", "υ": "u", "χ": "x",
    "γ": "y", "ω": "w", "η": "n", "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M",
    "Ν": "N", "Ο": "O", "Ρ": "P", "Τ": "T", "Υ": "Y", "Χ": "X",
})
NAME_RE = re.compile(r"^(?:LATIN LETTER SMALL CAPITAL|MODIFIER LETTER (?:SMALL|CAPITAL)|LATIN SMALL LETTER|LATIN CAPITAL LETTER) ([A-Z])$")

CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
JUNG = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
JONG = " ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ"
INVISIBLE = {"­", "͏", "ᅟ", "ᅠ", "ㅤ", "ﾠ"}


def _latinize(ch):
    if ord(ch) < 128:
        return ch
    t = ch.translate(CONF)
    if t != ch:
        return t
    try:
        m = NAME_RE.match(unicodedata.name(ch))
    except ValueError:
        return ch
    return m.group(1).lower() if m else ch


def _compose(s):
    """호환 자모(ㄱ..ㅣ) 나열을 음절로 묶는다: 초성+중성(+종성)."""
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c in CHO and i + 1 < len(s) and s[i + 1] in JUNG:
            L, V = CHO.index(c), JUNG.index(s[i + 1])
            T = 0
            if i + 2 < len(s) and s[i + 2] in JONG[1:] and not (i + 3 < len(s) and s[i + 3] in JUNG):
                T = JONG.index(s[i + 2])
            out.append(chr(0xAC00 + (L * 21 + V) * 28 + T))
            i += 3 if T else 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def restore(s):
    s = unicodedata.normalize("NFKC", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Cf" and c not in INVISIBLE)
    s = "".join(_latinize(c) for c in s)
    s = unicodedata.normalize("NFC", _compose(s))  # 조합 자모(U+1100~)는 NFC 로 음절이 된다
    return s


BLOCKS = {
    "fullwidth": [(0xFF01, 0xFF5E)], "enclosed": [(0x2460, 0x24FF), (0x2776, 0x2793), (0x1F100, 0x1F1FF), (0x3200, 0x32FF)],
    "math": [(0x1D400, 0x1D7FF)], "smallcap": [(0x1D00, 0x1DBF), (0x02B0, 0x02FF), (0xA720, 0xA7FF)],
    "cyr": [(0x0400, 0x052F)], "greek": [(0x0370, 0x03FF)], "cjamo": [(0x3131, 0x318E)], "jjamo": [(0x1100, 0x11FF)],
    "hangul": [(0xAC00, 0xD7A3)], "latin": [(0x41, 0x5A), (0x61, 0x7A)], "digit": [(0x30, 0x39)],
    "zw": [(0x200B, 0x200F), (0x2060, 0x206F), (0xFEFF, 0xFEFF), (0x00AD, 0x00AD)],
}
KEYS = list(BLOCKS) + ["nfkc_change", "restore_change", "mixed_tok", "len_log"]


def stats(s):
    n = max(len(s), 1)
    cnt = {k: 0 for k in BLOCKS}
    for ch in s:
        o = ord(ch)
        for k, rs in BLOCKS.items():
            if any(a <= o <= b for a, b in rs):
                cnt[k] += 1
                break
    v = {k: cnt[k] / n for k in BLOCKS}
    nk = unicodedata.normalize("NFKC", s)
    v["nfkc_change"] = sum(1 for a, b in zip(s, nk) if a != b) / n if len(nk) == len(s) else 1.0
    r = restore(s)
    v["restore_change"] = 1.0 - (sum(1 for a, b in zip(s, r) if a == b) / max(len(s), len(r), 1))
    toks = s.split()
    mixed = 0
    for t in toks:
        scripts = set()
        for ch in t:
            if ch.isalpha():
                scripts.add("L" if ord(ch) < 128 else ("H" if 0xAC00 <= ord(ch) <= 0xD7A3 else "O"))
        mixed += len(scripts) > 1 and "O" in scripts
    v["mixed_tok"] = mixed / max(len(toks), 1)
    v["len_log"] = __import__("math").log1p(len(s))
    return [v[k] for k in KEYS]
