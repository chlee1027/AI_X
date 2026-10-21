"""v4 글자 규칙 보강 (10-17). rules.py(v2·v3 동결)는 그대로 두고, 이 파일이 techniques 를 바꿔 낀다(use()).

개발 데이터에서 규칙이 켜지지 않은 HG 정답 100개를 보고 넣은 것(팀원 사이트·시험셋 미사용):
  PHONE_MIX : 숫자 자리에 O·o·I·l 을 넣고 사이에 공백·닮은 점을 끼운 전화번호 꼴(예: 「O 1 O - 1234」 「0I0。XXX」 「01o.」).
              rules.DIGIT_LETTER 는 붙여 쓴 꼴만 잡는다.
  HANGUL_LIKE : NFKC 로 풀면 한글이 되는 한글 아닌 글자(원·괄호 한글 ㉸ ㈚, 반각 자모). 유니코드 표준 성질만 쓴다.
              rules.lookalike 는 라틴 영문·숫자로 풀리는 것만 본다.
  DIGIT_FIX : rules.DIGIT_LETTER 가 순수 숫자 전화번호(010-1234)에도 켜지는 버그를 막는다(영문자가 하나는 있어야 켜짐).
  JL_BOTH   : 자모+라틴을 섞은 낱말은 v2 에서 HG 로만 냈다. 개발 정답은 HG 116, JAMO 46 으로 갈려 둘 다 내는 안을 개발 점수로 고른다.
숨김 규칙 보강(offscreen4·transparent4): render4.py 가 검사 때만 뽑는 특징(selfOv·cvh·zm·fop)을 읽는다. check_css.py 로 확인.
  개발 데이터 캐시에는 이 특징이 없어 개발 점수에는 영향이 없다(그래서 개발 점수로는 검증되지 않는다).
글자 항목은 개발 데이터 같은 사이트 뺀 5-fold 로 켜고 끈 점수를 비교해 고른다(exp_rules4.py).
"""
import re
import unicodedata

import rules
from rules import COMPAT, LAT, SYL, transparent, offscreen

PHONE_MIX = re.compile(r"(?<![A-Za-z])([0Oo])[ \t]?([1lI|])[ \t]?([0Oo])(?=[\s\-=.~·。．^]*[\dXx])")
OPTS = {"phone": True, "hangul_like": True, "jl_both": False, "digit_fix": True, "hg2": False, "numform": False, "bar": True}
# 10-20 hg2(진행보고서 7-57절): 개발 데이터에서 안 켜진 HG 정답 80개를 보고 넣은 일반 규칙 셋. 기본은 끔(모델 표지 hg2 로 켬).
#   (1) 전각 기호(U+FF01~FF5E 중 영문·숫자 밖, 예: ＋ ［ ］ ％): 요강 붙임1 「키릴·전각 문자」
#   (2) 한글로 풀리는 테두리 글자가 조합형 자모(U+1100~)로 풀리는 경우(예: ㉢)
#   (3) 도메인 점 자리의 가운뎃점(・ ･)과 「쩜」
FW_SYM = re.compile(r"[！-／：-＠［-｀｛-～]")
DOT2 = re.compile(r"[\w가-힣]\s*(?:[・･]|쩜)\s*(?:com|net|kr|co|org|top|xyz|io|me|shop|site|vip|bet|win|cc|tv|in|to)(?![A-Za-z])", re.I)


def hangul_like(c):
    if SYL.match(c) or COMPAT.match(c) or c.isascii():
        return False
    n = unicodedata.normalize("NFKC", c)
    return n != c and bool(re.search(r"[가-힣ㄱ-ㆎ]" if not OPTS.get("hg2") else r"[가-힣ㄱ-ㆎᄀ-ᇿ]", n))


def _numform(c):
    """로마 숫자·동그라미/괄호 숫자(공공 문서의 번호 기호). 10-21(진행보고서 7-78절)."""
    o = ord(c)
    return 0x2160 <= o <= 0x217F or 0x2460 <= o <= 0x24B5 or 0x2776 <= o <= 0x2793 or 0x3251 <= o <= 0x325F or 0x32B1 <= o <= 0x32BF


def homoglyph(text):
    why = rules.homoglyph(text)
    # 10-21(7-78절): 닮은꼴 글자가 번호 기호(Ⅱ ③ 등)뿐이면 공공 문서의 정상 표기다(정상 사이트 959 줄, 개발 정답 4). 옵션 numform.
    if OPTS.get("numform") and why and why[0].startswith("닮은꼴 문자로 쓴"):
        la = [c for c in text if not c.isspace() and rules.lookalike(c)]
        if la and all(_numform(c) for c in la):
            why = why[1:]
    if OPTS["digit_fix"] and "숫자 자리에 영문자(O·l·I)" in why:
        # rules.DIGIT_LETTER 는 [0Oo][1lI|][0Oo] 라 순수 숫자 「010-1234」 에도 켜진다. 영문자가 하나라도 있을 때만 남긴다.
        if not any(re.search(r"[A-Za-z|]", m.group(0)) for m in rules.DIGIT_LETTER.finditer(text)):
            why.remove("숫자 자리에 영문자(O·l·I)")
    if OPTS["phone"] and "숫자 자리에 영문자(O·l·I)" not in why:
        for m in PHONE_MIX.finditer(text):
            if any(not g.isdigit() for g in m.groups()):
                why.append("숫자 자리에 영문자(O·l·I, 띄어 씀)")
                break
    if OPTS["hangul_like"]:
        n = sum(1 for c in set(text) if hangul_like(c))
        if n:
            why.append(f"한글로 풀리는 테두리·반각 글자 {n}종")
    if OPTS.get("hg2"):
        n = len(set(FW_SYM.findall(text)))
        if n:
            why.append(f"전각 기호 {n}종")
        if DOT2.search(text):
            why.append("도메인 점 자리에 가운뎃점·「쩜」")
    return why


CALLNO = re.compile(r"^[가-힣]{1,3}\d{1,4}[ㄱ-ㅎ]$")  # 도서 청구기호의 저자기호 꼴(예: 환14ㅎ)


def jamo(text):
    why = rules.jamo(text)
    # 10-21(진행보고서 7-78절): 환경부 도서관 목록의 「환14ㅎ」(저자기호)가 낱자 자모 낱말로 잡혀 JAMO 오탐 101건.
    # 자모 분해 광고는 낱자를 여럿 쓴다(ㅋㅏㅈㅣㄴㅗ). 자모 낱말이 모두 저자기호 꼴이면 그 근거를 뺀다(개발 JAMO 정답 중 이 꼴 0).
    if why and any(w.startswith("낱자 자모를 섞은 낱말") for w in why):
        toks = [t for t in re.split(r"[\s\W_]+", text) if COMPAT.search(t) and (SYL.search(t) or len(COMPAT.findall(t)) >= 2) and not LAT.search(t)]
        # 「있다!ㅣ디스커버리」처럼 모음 ㅣ 를 세로 막대 대신 구분자로 쓴 것도 뺀다(개발 JAMO 정답 중 0, 정상 사이트 12 줄)
        if toks and all(CALLNO.match(t) or (OPTS.get("bar") and set(COMPAT.findall(t)) == {"ㅣ"}) for t in toks):
            why = [w for w in why if not w.startswith("낱자 자모를 섞은 낱말")]
    if OPTS["jl_both"]:
        n = sum(1 for tok in re.split(r"[\s\W_]+", text)
                if COMPAT.search(tok) and LAT.search(tok) and (SYL.search(tok) or len(COMPAT.findall(tok)) >= 1))
        if n:
            why.append(f"낱자 자모와 영문자를 섞은 낱말 {n}개")
    return why


def offscreen4(f):
    """rules.offscreen + render4 특징(검사 때만 있음). check_css.py 에서 빠졌던 방법."""
    why = offscreen(f)
    if f.get("selfOv") and not f.get("zeroOv"):
        why.append("자기 1px 상자 + overflow 숨김")
    if f.get("cvh"):
        why.append("content-visibility:hidden")
    if f.get("zm", 1) < 1 and f.get("fs", 16) * f.get("zm", 1) <= rules.OF_FONT:
        why.append(f"zoom 으로 글꼴 {f['fs'] * f['zm']:.2f}px")
    if f.get("frOff"):  # 10-19(7-37절): 이 요소를 품은 iframe 이 바깥 문서에서 화면 밖(scan4.frame_hidden, 검사 때만 있음)
        why.append("iframe 이 화면 밖")
    return why


def transparent4(f):
    why = transparent(f)
    if f.get("fop", 1) <= rules.TR_OPACITY:
        why.append(f"filter opacity {f['fop']:.2f}")
    if f.get("frOp", 1) <= rules.TR_OPACITY:  # 10-19(7-37절): 품은 iframe 의 누적 불투명도
        why.append(f"iframe 불투명도 {f['frOp']:.2f}")
    return why


def techniques(f, text):
    out = {}
    for name, fn, arg in (("TRANSPARENT", transparent4, f), ("OFFSCREEN", offscreen4, f),
                          ("HOMOGLYPH", homoglyph, text), ("JAMO", jamo, text)):
        w = fn(arg)
        if w:
            out[name] = w
    return out


def stack_skip(rows):
    """10-20 v9 규칙 S(진행보고서 7-44절): OF 근거가 3개 이상이고 그중 display:none 이 있으면 OF 를 끈다(접힌 메뉴·화면 낭독기용 숨김).
    개발 데이터에서 이 조합은 OF 정답 896 중 6, 정상 줄 1만여 개. 다른 기법은 그대로. 고친 줄 수를 돌려준다."""
    n = 0
    for r in rows:
        why = (r.get("rt") or {}).get("OFFSCREEN")
        if why and len(why) >= 3 and "display:none" in why:
            del r["rt"]["OFFSCREEN"]
            n += 1
    return n


def garble_skip(rows, ratio=0.3):
    """10-20(진행보고서 7-60절): 글자가 깨진 요소(물음표·U+FFFD 가 공백 뺀 글자의 30% 이상, 4자 이상)는 모든 기법에서 뺀다.
    인코딩이 깨진 글은 사람도 읽을 수 없어 광고 판정의 근거가 없다(공공기관 과기부 오탐 2건). 고친 줄 수를 돌려준다."""
    n = 0
    for r in rows:
        t = "".join((r.get("text") or "").split())
        if r.get("rt") and len(t) >= 4 and sum(c in "?�" for c in t) / len(t) >= ratio:
            r["rt"] = {}
            n += 1
    return n


def conj_boost(rows, ad, floor=0.99):
    """10-21(진행보고서 7-69절): 조합형 자모(U+1100~)가 든 요소는 광고 점수를 floor 로 올린다. 개발 음성 21,279 줄·정상 사이트 65만 줄에서 0 이라
    정상 글에는 쓰지 않는 위장으로 본다. ad(목록)를 고쳐 돌려준다."""
    ad = list(ad)
    for k, r in enumerate(rows):
        if rules.CONJ.search(r.get("text") or ""):
            ad[k] = max(ad[k], floor)
    return ad


def emit_all(rows, det):
    """10-21(진행보고서 7-81절): 광고로 판정된 요소에 규칙이 걸린 다른 기법도 함께 낸다(요강: 중첩이면 기법별 별도 객체).
    det = {(sid, i, t): (점수, [근거])} -> 같은 꼴."""
    key = {(r["sid"], r["i"]): r for r in rows}
    out = dict(det)
    for (sid, i, t), (p, why) in det.items():
        r = key.get((sid, i))
        if r is None:
            continue
        # 10-21(7-82절, 요강 결정): 조합형 자모 글은 자모 분해 하나만 쓴 것이라 HG 를 더하지 않는다. 규칙이 실제로 걸린 기법만 더한다.
        ts = dict(r.get("rt") or {})
        for t2, w2 in ts.items():
            if (sid, i, t2) not in out:
                out[(sid, i, t2)] = (p, list(w2) + [f"{t} 로 광고 판정된 같은 요소(중첩 기법)"])
    return out


def use(**opts):
    """train2.rule_cache 가 이 규칙을 쓰게 한다. 이미 계산된 rt 는 다시 계산해야 한다."""
    import train2
    OPTS.update(opts)
    train2.techniques = techniques
