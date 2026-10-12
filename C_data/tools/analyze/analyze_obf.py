"""저장한 원문 HTML 에서 '도박 광고 + 난독화' 요소를 찾고 난독화 특징을 센다 (실측 조합 찾기).

오프라인 렌더링(JS 끔, 네트워크 전부 차단)으로 요소마다 보이는지 확인하고,
느슨하게 정규화한 텍스트(NFKC·제로폭 제거·자모 재결합·기호/공백 제거)에서 도박 어휘가 나오면 후보로 잡는다.

특징
  fullwidth   전각 영숫자·기호 (U+FF01~FF5E)
  cjk_punct   。〃【】「」〙 같은 CJK 문장부호를 영문 도메인·낱말에 섞음
  jamo        호환자모·조합자모
  zero_width  제로폭·방향 제어 문자
  homoglyph   라틴 낱말 속 키릴·그리스 문자, 또는 낱말 앞뒤에 붙인 그리스·오검 문자
  symbol_sep  낱말 사이에 끼운 수학·화살표·도형·딩뱃 기호
  emoji       이모지
  masking     *** 로 키워드 가림
  hidden      화면에 안 보임 (렌더링 면적 0)
  entity      원문 html 에서 이 텍스트 근처가 숫자 엔티티로 적힘

사용: python analyze_obf.py out.json file.html [file.html ...]
"""
import json
import re
import sys
import unicodedata
from pathlib import Path

from playwright.sync_api import sync_playwright

KW = re.compile(r"카지노|바카라|토토|토지노|슬롯|먹튀|놀이터|꽁머니|첫충|가입코드|룰렛|베팅|배팅|홀덤|파워볼|에볼루션|"
                r"카톡|까톡|ka톡|텔레|벳|바둑이|릴게임|야마토|casino|baccarat|toto|bet|"
                # 도박 외 불법광고: 의약품·성매매·불법대출
                r"비아그라|시알리스|자이데나|레비트라|최음제|흥분제|출장안마|출장마사지|출장|조건만남|오피|룸싸롱|"
                # 「일수」는 「높일 수」 같은 일반 문장에 걸려 뺐다
                r"작업대출|내구제|대포통장|대포폰|급전|캬톡", re.I)

JS = r"""
() => {
  // JS 로 화면을 켜는 사이트(body style="display:none")는 JS 를 끈 렌더링에서 전체가 숨김으로 잡히므로 풀어 준다
  for (const e of [document.documentElement, document.body]) {
    if (getComputedStyle(e).display === 'none' || getComputedStyle(e).visibility === 'hidden' || getComputedStyle(e).opacity === '0') {
      e.style.setProperty('display', 'block', 'important'); e.style.setProperty('visibility', 'visible', 'important');
      e.style.setProperty('opacity', '1', 'important');
    }
  }
  const out = [];
  for (const el of document.body.querySelectorAll('*')) {
    if (['SCRIPT','STYLE','NOSCRIPT'].includes(el.tagName)) continue;
    let own = '';
    for (const n of el.childNodes) if (n.nodeType === 3) own += n.nodeValue;
    if (own.trim().length < 3) continue;
    const r = el.getBoundingClientRect();
    const vis = el.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}) && r.width > 1 && r.height > 1
                && parseFloat(getComputedStyle(el).fontSize) > 1;
    // 간단한 경로
    const path = []; for (let e = el; e && e !== document.body; e = e.parentElement) {
      path.unshift(e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + [...e.classList].slice(0,2).map(c => '.' + c).join(''));
    }
    out.push({text: own, visible: vis, path: path.join(' > ')});
  }
  return out;
}
"""

CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
JUNG = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"


def _cho(w: str) -> str:
    return "".join(CHO[(ord(c) - 0xAC00) // 588] for c in w)


# 다른 자모와 붙어 있으면(ㅋㅋㅋ, ㅌㅌㅌ) 웃음·반복으로 보고 세지 않는다
CHO_ABBR = re.compile("(?<![ㄱ-ㅣ])(?:" + "|".join(sorted({_cho(w) for w in KW.pattern.split("|")
                                                         if re.fullmatch("[가-힣]{2,}", w)}, key=len, reverse=True))
                      + ")(?![ㄱ-ㅣ])")


def recombine(s: str) -> str:
    out, i = [], 0
    s = s.replace(" ", "")
    while i < len(s):
        if i + 1 < len(s) and s[i] in CHO and s[i + 1] in JUNG:
            out.append(chr(0xAC00 + (CHO.index(s[i]) * 21 + JUNG.index(s[i + 1])) * 28))
            i += 2
        else:
            out.append(s[i])
            i += 1
    return "".join(out)


def loose(s: str) -> str:
    s = unicodedata.normalize("NFKC", s)
    s = re.sub("[​-‏⁠-⁤﻿᠎‪-‮­͏ᅟᅠㅤﾠ]", "", s)
    s = recombine(s)
    return re.sub(r"[\s\W_]+", "", s)


SPELL_VARIANT = re.compile(r"캬톡|꺄톡|카토옥|카똑|칵톡|캇톡|카톡끄|카.ㅌ.ㅗ.ㄱ|텔래그램|탤레그램|탤래그램|텔레그렘|텔그램|뗄레그램|떼레그램|"
                           r"테레그램|텔래|탤레|탤래|비아그랴|비아구라|비아그롸|시알리쓰|씨알리쓰|카쥐노|카지뇨|까지노|바까라|바카롸|"
                           r"토토싸이트|먹뛰|놀이털|홀뎜|홀듬|슬럿사이트")


def features(t: str) -> list[str]:
    f = []
    if re.search("[！-～]", t):
        f.append("fullwidth")
    if re.search("[A-Za-z0-9][。〃【】「」〙〘][A-Za-z0-9]|[〃。][A-Z]", t) or \
       re.search("〃\\s*\\S+[.。．]\\s*(?:com|net|kr|top|xyz)\\s*〃|(?:com|net|COM|NET)〃", t, re.I):
        f.append("cjk_punct")
    # 문장부호 바꿔치기: 전화번호의 별난 대시(―﹣‒⸻), 다른 문자권 쉼표(، ˏ ˎ ‚ ¸)
    # 전화번호 숫자 사이에 대시 대신 모음 자모 ㅡ 를 쓴 것(０１0ㅡ５8l５ㅡ２2６2)도 같은 바꿔치기로 센다. 가린 번호의 X 도 숫자 자리로 본다
    if len(re.findall("[―﹣‒⸻،ˏˎ‚¸]", t)) + len(re.findall("(?<=[0-9０-９oOlIX])ㅡ(?=[0-9０-９oOlIX])", t)) >= 2:
        f.append("punct_variant")
    # 자모 분해: 초성 다음에 (공백 넣어) 중성이 와서 음절로 다시 묶이는 것 (ㅋ ㅏ톡, ㅋㅏ지노)
    if re.search(f"[{CHO}]\\s?[{JUNG}]|[ᄀ-ᄒ][ᅡ-ᅵ]", t):
        f.append("jamo_split")
    # 자모·괄호 한글 구분자: 낱자 자모(ㆍ 제외)나 ㈙㉤ 같은 괄호·원 한글을 따로 떨어진 토큰으로 끼움
    if len(re.findall("(?:^|\\s)[ㄱ-ㆌㆎ㈀-㈞㉠-㉾](?=\\s|$)", t)) >= 2:
        f.append("jamo_sep")
    # 한국어 문장 속에 일본어 가나 한 글자씩을 끼워 도메인·키워드를 감쌈
    if len(re.findall(r"(?:^|\s)[぀-ヿ](?=\s|[가-힣A-Za-z０-９Ａ-Ｚａ-ｚ])", t)) >= 2:
        f.append("kana_sep")
    # 보이지 않는 문자: 제로폭·방향 제어·소프트하이픈·한글 채움 문자 (ETC 분석기와 같은 범위)
    if re.search("[​-‏⁠-⁤﻿᠎‪-‮­͏ᅟᅠㅤﾠ]", t):
        f.append("zero_width")
    # 동형문자: 라틴 낱말 속에 키릴·그리스 글자가 붙어 있음 (글자 바꿔치기)
    if re.search("[A-Za-z][Ѐ-ӿͰ-Ͽ]|[Ѐ-ӿͰ-Ͽ][A-Za-z]", t):
        f.append("homoglyph")
    # 그리스·오검 글자를 한글 낱말 사이 구분자로 쓴 것(ψ, δ, ᚌ)은 기호 구분자로 센다
    greek_sep = re.findall("(?<=[가-힣\\s\\]])[Ͱ-Ͽ -᚟](?=[가-힣\\s\\[0-9])", t)
    syms = [ch for ch in t if unicodedata.category(ch) in ("Sm", "So") and not (0x1F300 <= ord(ch) <= 0x1FAFF)
            and ch not in "❤☑✅⭐★☆♥" and ord(ch) > 0x2000] + greek_sep
    if len(syms) >= 2:
        f.append("symbol_sep")
    if re.search("[\U0001F300-\U0001FAFF☀-➿]", t):
        f.append("emoji")
    if re.search(r"\*{3,}", t):
        f.append("masking")
    # 자모로 영문자 바꾸기: TㅇP·tㅇp(ㅇ=o), ㄹr인(ㄹ+r=라)
    if re.search("[A-Za-z][ㅇㅁ][A-Za-z]|[ㄱ-ㅎ][A-Za-z][가-힣]", t):
        f.append("jamo_homoglyph")
    # 작은 대문자·IPA 글자로 영문 쓰기 (ʜᴏɴɢʙᴏ)
    if len(re.findall("[ᴀ-ᴫʀ-ʯ]", t)) >= 2:
        f.append("smallcaps")
    # 원·괄호 한글로 음절 바꾸기 (㉸톡 = 카톡)
    if re.search("[㈀-㈞㉠-㉾][가-힣]", t):
        f.append("enclosed_hangul")
    # 광고 낱말을 초성만으로 줄여 씀 (ㅌㅌ사이트 = 토토사이트, ㅂㅋㄹ = 바카라). 약어는 KW 의 한글 낱말에서 만든다 (2026-10-12)
    if CHO_ABBR.search(t):
        f.append("jamo_abbrev")
    # 낱말 속에 홀로 낀 자음 (텔ㄹ그ㄹ = 텔레그램)
    if re.search("[가-힣][ㄱ-ㅎ][가-힣]|[가-힣][ㄱ-ㅎ](?=[\\s:：@]|$)", t):
        f.append("jamo_inword")
    # 수학용 영숫자(𝐊𝟖 등)·화폐 기호를 글자 대신(₭=K)
    if re.search("[\U0001D400-\U0001D7FF]", t):
        f.append("math_alnum")
    if re.search("[₠-⃏]{1,}[\\s]*[A-Za-z0-9]|[A-Za-z][₠-⃏]", t):
        f.append("currency_glyph")
    # 도메인의 점을 「닷」「쩜」·쉼표로 바꿈 (쩜컴·닷컴 포함)
    if re.search(r"[A-Za-z0-9]\s*(닷|쩜)\s*(com|net|kr|top|xyz|org|컴)|[A-Za-z0-9]\s*,\s*(com|net|kr|top|xyz)\b|[A-Za-z0-9]ㆍ[A-Za-z]", t, re.I):
        f.append("dot_sub")
    # 도메인 글자 사이에 공백 (K O C 1 2 3 4 。COM, TTB1234 。 C OM)
    if re.search(r"[A-Za-z0-9Ａ-Ｚａ-ｚ０-９｜](?:\s+[A-Za-z0-9Ａ-Ｚａ-ｚ０-９｜]+){2,}\s*[.。．]\s*[CcＣｃ]\s*[OoＯｏ]\s*[MmＭｍ]"
                 r"|[.。．]\s*[CcＣｃ]\s+[OoＯｏ]\s*[MmＭｍ]|[.。．]\s*[CcＣｃ][OoＯｏ]\s+[MmＭｍ]", t):
        f.append("domain_spacing")
    # 원·괄호 숫자/영문으로 번호 적기 (ⓞ①ⓞ, ⑵⑷)
    if len(re.findall("[①-⓿❶-➓]", t)) >= 2:
        f.append("enclosed_alnum")
    # 최상위 도메인 대소문자 섞기 (CoM·cOm·ｃoM)
    if re.search(r"[.。．,닷쩜]\s*(?=[A-Za-zＡ-Ｚａ-ｚ]{2,3}\b)(?:[A-Za-zＡ-Ｚａ-ｚ]*[a-zａ-ｚ][A-ZＡ-Ｚ]|[A-ZＡ-Ｚ][a-zａ-ｚ]+[A-ZＡ-Ｚ])", t):
        f.append("case_mix")
    # 키워드 중간에 공백·구분 기호를 넣어 쪼갬 (원문엔 키워드가 없는데 공백·기호를 빼면 나옴)
    plain_kw = set(m.group(0) for m in KW.finditer(t))
    split_kw = set(m.group(0) for m in KW.finditer(re.sub(r"[\s.\-·_/|,]+", "", t))) - plain_kw
    if split_kw:
        f.append("spacing")
    # 키워드 일부러 틀리게 쓰기: 필터 사전에 없는 철자로 바꿈 (캬톡·카토옥·텔래그램·비아그랴)
    if SPELL_VARIANT.search(t):
        f.append("spelling_variant")
    # 숫자 자리에 영문 o/O/l 을 섞은 번호 (o1o, 01o-, l0 등)
    # 구분자에는 자모 ㅡ 와 가운뎃점도 들어간다 (５8l５ㅡ２2６2)
    if re.search(r"(?<![A-Za-z])(?:[oOlI][\s\-―﹣‒⸻–—ㅡ·.]*\d|\d[\s\-―﹣‒⸻–—ㅡ·.]*[oOlI])(?:[\s\-―﹣‒⸻–—ㅡ·.]*[\doOlI]){4,}", t) or \
       re.search(r"\d[\s,]+[IlOo](?:[\s,]+[IlOo])?[\s,]+\d", t):
        f.append("digit_sub")
    return f


def main(out: str, files: list[str]) -> None:
    results = []
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        ctx = b.new_context(java_script_enabled=False, viewport={"width": 1280, "height": 900})
        ctx.route("**/*", lambda r: r.abort())
        pg = ctx.new_page()
        for f in files:
            raw = Path(f).read_bytes().decode("utf-8", "replace")
            meta_p = Path(f).with_suffix(".json")
            url = json.loads(meta_p.read_text(encoding="utf-8"))["url"] if meta_p.exists() else ""
            pg.set_content(raw, wait_until="domcontentloaded")
            for it in pg.evaluate(JS):
                t = it["text"]
                if not KW.search(loose(t)):
                    continue
                fs = features(t)
                if not it["visible"]:
                    fs.append("hidden")
                # 원문에서 엔티티로 적혔는지 (텍스트 앞 6자가 원문에 그대로 없고 엔티티가 근처에 있으면)
                head = t.strip()[:6]
                if head and head not in raw and re.search(r"&#\d{3,6};", raw):
                    fs.append("entity")
                results.append({"file": str(f), "url": url, "path": it["path"], "visible": it["visible"],
                                "features": fs, "text": t.strip()[:400]})
        b.close()
    Path(out).write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    combos = [r for r in results if len(set(r["features"])) >= 2]
    print(f"도박 문구 요소 {len(results)} / 특징 2개 이상 {len(combos)}")
    from collections import Counter
    print(Counter(tuple(sorted(set(r["features"]))) for r in combos).most_common(30))


if __name__ == "__main__":
    # @목록.txt 를 받으면 그 안의 경로들로 펼친다 (Windows 명령줄 길이 제한 회피)
    files = []
    for a in sys.argv[2:]:
        files += Path(a[1:]).read_text(encoding="utf-8-sig").splitlines() if a.startswith("@") else [a]
    main(sys.argv[1], files)
