"""기법 판정 규칙 (v2, 10-17). 학습하지 않는다. 판정마다 근거 문장을 같이 돌려준다(결과 화면용).

TRANSPARENT / OFFSCREEN: 요강 붙임1 정의를 브라우저 계산값으로 옮긴 것(render.py 의 f).
HOMOGLYPH / JAMO: 글자 규칙. 유니코드 표준(NFKC, 문자 이름) + 개발 데이터에서 확인한 실례 유형
  (숫자 자리의 O·l·I, 자모+라틴 섞은 낱말, 도메인 점 자리의 닮은 점, 낱자 자모+음절 섞기, 조합형 자모).
"""
import re
import unicodedata

from textfeat import _latinize

TR_OPACITY = 0.05      # 누적 불투명도 이하면 투명
TR_ALPHA = 0.05        # 글자색·채움색 알파 이하면 투명
TR_CONTRAST = 1.15     # 글자색과 실제 배경색 대비 미만이면 투명(배경 이미지가 있으면 판정 안 함)
OF_FONT = 1.0          # 글꼴 크기 이하(px)면 화면 밖 은닉(요강: font-size 0~1px)
OF_SCALE = 0.05        # transform 배율 이하면 보이지 않음

NAME_LATIN = re.compile(r"LATIN (?:CAPITAL |SMALL )?LETTER [A-Z]$|DIGIT (?:ZERO|ONE|TWO|THREE|FOUR|FIVE|SIX|SEVEN|EIGHT|NINE)$")
COMPAT = re.compile(r"[ㄱ-ㆎ]")
CONJ = re.compile(r"[ᄀ-ᇿꥠ-꥿ힰ-퟿]")
SYL = re.compile(r"[가-힣]")
LAT = re.compile(r"[A-Za-z]")
# 숫자 자리에 들어간 O/o/l/I: 전화번호 꼴(0x0-xxxx-xxxx) 또는 숫자 사이
DIGIT_LETTER = re.compile(r"(?<![A-Za-z])[0Oo][1lI|][0Oo][\s\-=.~·]*\d{3,4}|\d[Oo]\d|(?<![A-Za-z])[Oo][1lI][Oo](?![A-Za-z])")
# 도메인 점 자리의 닮은 점
DOT_GLYPH = re.compile(r"[\w가-힣][\s]*[。｡․．·ㆍ•∙⋅][\s]*(?:com|net|kr|co|org|top|xyz|io|me|shop|site|vip|bet|win|cc|tv|in|to)(?![A-Za-z])", re.I)


def transparent(f):
    why = []
    if f.get("op", 1) <= TR_OPACITY:
        why.append(f"누적 불투명도 {f['op']:.2f}")
    if f.get("colA", 1) <= TR_ALPHA:
        why.append("글자색 알파 0")
    if f.get("fillA", 1) <= TR_ALPHA:
        why.append("글자 채움색 알파 0")
    if not f.get("bgImg") and f.get("contrast", 21) < TR_CONTRAST:
        why.append(f"배경과 대비 {f['contrast']:.2f}")
    return why


def offscreen(f):
    why = []
    if f.get("dispNone"):
        why.append("display:none")
    if f.get("visHid"):
        why.append("visibility:hidden")
    if f.get("fs", 16) <= OF_FONT:
        why.append(f"글꼴 {f['fs']:.1f}px")
    if f.get("off"):
        why.append("화면 밖 좌표")
    if f.get("indent"):
        why.append("음수 들여쓰기")
    if f.get("clip"):
        why.append("clip 으로 잘림")
    if f.get("zeroOv"):
        why.append("1px 상자 + overflow 숨김")
    if f.get("scale", 1) <= OF_SCALE:
        why.append("transform 배율 0")
    return why


def lookalike(c):
    """ASCII 가 아닌 글자가 NFKC·라틴화 뒤 ASCII 영문·숫자가 되면 닮은꼴 글자."""
    if c.isascii() or SYL.match(c) or COMPAT.match(c) or CONJ.match(c):
        return False
    n = unicodedata.normalize("NFKC", c)
    m = "".join(_latinize(x) for x in n)
    if len(m) >= 1 and m.isascii() and m.isalnum():
        return True
    # NFKC 로 안 풀리는 테두리 글자(예: NEGATIVE SQUARED LATIN CAPITAL LETTER H)는 문자 이름으로
    try:
        nm = unicodedata.name(c)
    except ValueError:
        return False
    return bool(NAME_LATIN.search(nm))


def homoglyph(text):
    why = []
    toks = [t for t in re.split(r"\s+", text) if t]
    n = sum(1 for t in toks if any(lookalike(c) for c in t))
    if n:
        why.append(f"닮은꼴 문자로 쓴 영문·숫자 낱말 {n}개")
    if DIGIT_LETTER.search(text):
        why.append("숫자 자리에 영문자(O·l·I)")
    if any(COMPAT.search(t) and LAT.search(t) for t in toks):
        why.append("자모와 영문자를 섞은 낱말")
    if DOT_GLYPH.search(text):
        why.append("도메인 점 자리에 닮은 점")
    return why


def jamo(text):
    why = []
    if CONJ.search(text):
        why.append("조합형 자모(U+1100~)")
    n = 0
    for tok in re.split(r"[\s\W_]+", text):
        if COMPAT.search(tok) and (SYL.search(tok) or len(COMPAT.findall(tok)) >= 2):
            if LAT.search(tok):
                continue  # 자모+영문은 닮은꼴로 본다
            n += 1
    if n:
        why.append(f"낱자 자모를 섞은 낱말 {n}개")
    return why


def techniques(f, text):
    """-> {기법: [근거, ...]}"""
    out = {}
    for name, fn, arg in (("TRANSPARENT", transparent, f), ("OFFSCREEN", offscreen, f),
                          ("HOMOGLYPH", homoglyph, text), ("JAMO", jamo, text)):
        w = fn(arg)
        if w:
            out[name] = w
    return out
