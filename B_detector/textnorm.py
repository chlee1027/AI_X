"""글자 정규화와 글자 기반 기법 신호(HOMOGLYPH · JAMO).

정규화(개발 계획 5.1): NFKC -> Cf 제거 -> 키릴·그리스 닮은꼴 폴딩 -> 호환자모 재결합 -> 구분자 제거
"""
import re
import unicodedata

# 키릴·그리스 -> 라틴 (실측에서 본 것 위주)
CONFUSABLE = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "к": "k", "м": "m", "т": "t", "н": "h",
    "в": "b", "г": "r", "и": "n", "л": "n", "ѕ": "s", "і": "i", "ј": "j", "ԁ": "d", "һ": "h", "ԛ": "q", "ԝ": "w",
    "А": "A", "В": "B", "Е": "E", "К": "K", "М": "M", "Н": "H", "О": "O", "Р": "P", "С": "C", "Т": "T", "Х": "X",
    "У": "Y", "І": "I", "Ј": "J", "Ѕ": "S",
    "α": "a", "β": "b", "ε": "e", "ι": "i", "κ": "k", "ν": "v", "ο": "o", "ρ": "p", "τ": "t", "υ": "u", "χ": "x",
    "σ": "o", "η": "n", "ω": "w", "γ": "y",
    "Α": "A", "Β": "B", "Ε": "E", "Ζ": "Z", "Η": "H", "Ι": "I", "Κ": "K", "Μ": "M", "Ν": "N", "Ο": "O", "Ρ": "P",
    "Τ": "T", "Υ": "Y", "Χ": "X",
    "ʜ": "h", "ᴏ": "o", "ɴ": "n", "ɢ": "g", "ʙ": "b", "ᴅ": "d", "ᴄ": "c", "ᴋ": "k", "ɪ": "i", "ᴍ": "m", "ʀ": "r",
    "ᴀ": "a", "ᴇ": "e", "ᴛ": "t", "ᴜ": "u", "ᴠ": "v", "ᴡ": "w", "ᴢ": "z", "ʟ": "l", "ᴘ": "p", "ꜱ": "s", "ʏ": "y",
    "。": ".", "․": ".", "·": ".", "｡": ".",
})

# 호환자모 -> 초성/중성/종성 인덱스
CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
JUNG = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
JONG = ["", "ㄱ", "ㄲ", "ㄳ", "ㄴ", "ㄵ", "ㄶ", "ㄷ", "ㄹ", "ㄺ", "ㄻ", "ㄼ", "ㄽ", "ㄾ", "ㄿ", "ㅀ", "ㅁ", "ㅂ", "ㅄ", "ㅅ",
        "ㅆ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"]
CF_RE = re.compile(r"[­​-‏⁠-⁤﻿͏᠎]")


def recombine_jamo(s):
    """ㅂㅏㅋㅏㄹㅏ -> 바카라. 호환자모 초성+중성(+종성)을 음절로."""
    out = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c in CHO and i + 1 < n and s[i + 1] in JUNG:
            L, V = CHO.index(c), JUNG.index(s[i + 1])
            T = 0
            if i + 2 < n and s[i + 2] in JONG[1:] and not (i + 3 < n and s[i + 3] in JUNG):
                T = JONG.index(s[i + 2])
                i += 1
            out.append(chr(0xAC00 + (L * 21 + V) * 28 + T))
            i += 2
        else:
            out.append(c)
            i += 1
    return "".join(out)


def normalize(s, keep_space=True):
    s = CF_RE.sub("", str(s))
    s = unicodedata.normalize("NFKC", s)
    s = s.translate(CONFUSABLE)
    # NFKC 가 호환자모를 조합자모로 보내므로, 조합자모를 다시 호환자모로 돌린 뒤 재결합
    s = "".join(_to_compat(c) for c in s)
    s = recombine_jamo(s)
    s = unicodedata.normalize("NFC", s)
    s = s.lower()
    if not keep_space:
        s = re.sub(r"[\s\W_]+", "", s)
    else:
        s = re.sub(r"\s+", " ", s).strip()
    return s


_C2 = {}
for _ch in CHO:
    _C2[unicodedata.normalize("NFKC", _ch)] = _ch
for _ch in JUNG:
    _C2[unicodedata.normalize("NFKC", _ch)] = _ch
for _ch in JONG[1:]:
    _C2.setdefault(unicodedata.normalize("NFKC", _ch), _ch)


def _to_compat(c):
    return _C2.get(c, c)


# ---------------------------------------------------------------- 기법 신호

def _rng(c, a, b):
    return a <= ord(c) <= b


HG_RANGES = [(0xFF01, 0xFF5E), (0x2460, 0x24FF), (0x2776, 0x2793), (0x1D400, 0x1D7FF), (0x1F100, 0x1F1FF),
             (0x1D00, 0x1D7F), (0x2070, 0x209F), (0x3200, 0x32FF), (0x0250, 0x02AF), (0xA730, 0xA7FF),
             (0x2100, 0x214F), (0x24B6, 0x24E9)]
SKIP_NUM_MARK = True
DOT_SUB = set("。․｡．")
CYR_GR = [(0x0370, 0x03FF), (0x0400, 0x04FF)]
COMPAT_JAMO = (0x3131, 0x318E)
CONJ_JAMO = [(0x1100, 0x11FF), (0xA960, 0xA97F), (0xD7B0, 0xD7FF)]
JAMO_VOWEL = set(JUNG)
LAUGH = set("ㅋㅎㅠㅜㅡㅇ")
DIGIT_LETTER = re.compile(r"(?<![A-Za-z0-9])[OoㅇＯ○0][1lIｌ|ㅣ][OoㅇＯ○0](?![A-Za-z])")


UNIT_SIGN = set("℃℉")  # ℃ ℉. 기상청 기온 표기. 학습 몫 양성에 0건
CJK_RE = re.compile(r"[぀-ヿ㐀-鿿]")
HANGUL_RE = re.compile(r"[가-힣]")


def _fw_punct(c):
    return _rng(c, 0xFF01, 0xFF5E) and not c.isalnum()


def _latin_adj(t, c):
    """t 안의 c 가운데 하나라도 앞뒤에 영문·숫자(전각 포함)가 붙어 있는가.
    ․(U+2024)는 한글 공문서에서 가운뎃점(「접수․처리」)으로 쓴다. 학습 몫 양성 6건은 모두 도메인 점 자리(영문·숫자 옆)다"""
    for i, ch in enumerate(t):
        if ch == c and any(re.match(r"[A-Za-z0-9０-９Ａ-Ｚａ-ｚ]", x)
                           for x in (t[i - 1:i], t[i + 1:i + 2]) if x):
            return True
    return False


def hg_signal(text):
    """닮은꼴 글자 위장 신호의 종류 목록(빈 목록이면 신호 없음)."""
    sig = set()
    # 한글 없이 한자·가나로 쓴 글(외국어판 누리집)은 전각 문장부호와 。가 원래 표기다. 학습 몫에 이런 글은 0건이고,
    # 한글 광고에 섞인 전각 부호(［님。com］, 사용방법：)는 그대로 잡는다. 전각 영문·숫자는 면제하지 않는다
    cjk_only = bool(CJK_RE.search(text)) and not HANGUL_RE.search(text)
    toks = re.split(r"\s+", text)
    for t in toks:
        if not t:
            continue
        has_lat = any("a" <= c.lower() <= "z" for c in t)
        has_hang = any(_rng(c, 0xAC00, 0xD7A3) for c in t)
        for c in t:
            if c in UNIT_SIGN or (cjk_only and (_fw_punct(c) or c == "。")):
                continue
            if c not in "ⓒⒸⓡⓇ" and any(_rng(c, a, b) for a, b in HG_RANGES):
                # 원·괄호·마침표 숫자(① ⑴ ⒈, U+2460~249B)는 한글 문서의 번호 매김에 흔하다(실제 누리집 기사 제목 「시리즈 ②」)
                if SKIP_NUM_MARK and _rng(c, 0x2460, 0x249B):
                    continue
                # 국기 그림문자 하나(지역 표시 글자 두 개)는 꾸민 글자가 아니다. 셋 이상 이어지면 글자 꾸밈으로 본다
                if _rng(c, 0x1F1E6, 0x1F1FF) and sum(_rng(x, 0x1F1E6, 0x1F1FF) for x in t) <= 2:
                    continue
                # 괄호·원 한글(U+3200대)은 글자에 붙어 쓰일 때만(㉸톡). 홀로 구분자(㈕)로 쓰면 위장이 아니다
                if _rng(c, 0x3200, 0x32FF) and len(t) == 1:
                    continue
                # ㈜(주식회사)·㈔(사단법인)는 회사·법인 이름에 붙여 쓰는 표준 약자다(실제 누리집 「NICE평가정보㈜」).
                # 학습 몫에서 ㈜가 든 양성은 전각 영숫자 같은 다른 신호도 함께 있다
                if c in "㈜㈔":
                    continue
                sig.add("styled_char")
            if any(_rng(c, a, b) for a, b in CYR_GR) and (has_lat or has_hang or any(ch.isdigit() for ch in t)):
                sig.add("cyr_gr_mix")
            if c in DOT_SUB and not (c == "․" and not _latin_adj(t, c)):
                sig.add("dot_sub")
        # ㅋr 꼴: 호환자모 바로 뒤 라틴 소문자
        if re.search(r"[ㄱ-ㅎ][a-z]", t):
            sig.add("hangul_lookalike")
    # 맞은 세 글자 자체에 숫자 아닌 글자가 섞여야 한다. 따로 보면 주소의 「m=010707」과 「reload」의 lo 가 함께 걸린다
    if any(not m.group().isdigit() for m in DIGIT_LETTER.finditer(text)):
        sig.add("digit_letter")
    return sorted(sig)


def jamo_signal(text):
    sig = set()
    if any(any(_rng(c, a, b) for a, b in CONJ_JAMO) for c in text):
        sig.add("conjoining")
    for t in re.split(r"\s+", text):
        # 아래아(ㆍ U+318D)는 한글 문서에서 가운뎃점으로 흔히 쓴다(전화ㆍ팩스) -> 자모로 세지 않는다
        jam = [c for c in t if _rng(c, *COMPAT_JAMO) and c != "ㆍ"]
        if not jam:
            continue
        if all(c in LAUGH for c in jam) and not any(_rng(c, 0xAC00, 0xD7A3) for c in t):
            continue  # ㅋㅋ ㅠㅠ 만
        if any(c in JAMO_VOWEL for c in jam) and any(c in CHO for c in jam):
            sig.add("decomposed")
        elif any(_rng(c, 0xAC00, 0xD7A3) for c in t) or re.search(r"[A-Za-z0-9@]", t):
            sig.add("jamo_inword")
    return sorted(sig)
