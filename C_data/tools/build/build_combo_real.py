"""실측 난독화 조합 -> combo_real.yaml (생성 없음, 실제 페이지에서 잘라낸 것만).

입력: analyze_obf.py 결과(obf_analysis.json)
조합 기준: 회피용 특징이 2가지 이상 (장식용 이모지는 세지 않는다)
중복: 같은 글이 두 게시판 주소로 보이는 것(강화군 clinic/bbs)은 텍스트로 합치고,
      같은 사이트·같은 특징 조합은 최대 PER_KEY 개만 둔다 (한 업자 캠페인이 데이터를 덮지 않게)
개인정보: 전화번호 꼴 숫자열·이메일은 html·evidence 양쪽에서 같은 방식으로 가린다 (난독화 모양은 남긴다)

사용: python build_combo_real.py obf_analysis.json out.yaml
"""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from playwright.sync_api import sync_playwright

PER_KEY = 7  # 2026-10-04 200개로 늘리며 4에서 7로 (공백만 다른 중복은 finalize_combo.py 가 합친다)
STRONG = re.compile(r"카지노|바카라|토토|토지노|슬롯|먹튀|놀이터|꽁머니|첫충|가입코드|홀덤|파워볼|바둑이|릴게임|야마토|바다이야기|"
                    r"비아그라|시알리스|자이데나|레비트라|카마그라|최음제|흥분제|출장안마|출장마사지|출장샵|조건만남|오피|룸싸롱|"
                    r"내구제|작업대출|대포통장|대포폰|카톡|캬톡|까톡|ka톡|텔레그램|찌라시|casino|toto|baccarat", re.I)
IGNORE = {"emoji"}
# 대회 기법 코드로 옮길 때: 요강 4종에 들어가는 것과 ETC(제안 유형명)로 갈 것
OFFICIAL = {"fullwidth": "HOMOGLYPH", "cjk_punct": "HOMOGLYPH", "homoglyph": "HOMOGLYPH", "math_alnum": "HOMOGLYPH",
            "currency_glyph": "HOMOGLYPH", "digit_sub": "HOMOGLYPH", "enclosed_alnum": "HOMOGLYPH",
            "jamo_split": "JAMO", "hidden": "OFFSCREEN", "jamo_homoglyph": "HOMOGLYPH", "smallcaps": "HOMOGLYPH",
            "enclosed_hangul": "HOMOGLYPH", "jamo_inword": "JAMO",
            "jamo_abbrev": "JAMO", "same_color": "TRANSPARENT"}
ETC_NAME = {"zero_width": "ZERO_WIDTH", "entity": "ENCODING", "kana_sep": "KANA_SEPARATOR",
            "domain_spacing": "DOMAIN_SPACING", "punct_variant": "PUNCT_VARIANT",
            "jamo_sep": "JAMO_SEPARATOR", "symbol_sep": "SYMBOL_SEPARATOR", "spacing": "KEYWORD_SPACING",
            "dot_sub": "DOT_SUBSTITUTION", "case_mix": "CASE_MIX", "masking": "KEYWORD_MASKING",
            "spelling_variant": "SPELLING_VARIANT"}
DESC = {"fullwidth": "전각 영숫자", "cjk_punct": "전각 마침표 등 CJK 문장부호로 도메인 점 대체", "homoglyph": "그리스·오검 등 다른 문자 섞기",
        "math_alnum": "수학용 영숫자", "currency_glyph": "화폐 기호로 글자 대체", "digit_sub": "숫자 자리에 영문 o·I 치환",
        "jamo_split": "자모 분해", "jamo_sep": "낱자 자모·괄호 한글 구분자", "kana_sep": "일본어 가나 구분자",
        "symbol_sep": "특수기호 구분자", "spacing": "키워드 사이 공백·쉼표·하이픈", "dot_sub": "도메인 점을 닷·쩜·쉼표로",
        "case_mix": "최상위 도메인 대소문자 섞기", "masking": "*** 가림", "zero_width": "제로폭 문자", "entity": "숫자 엔티티",
        "hidden": "화면 숨김", "domain_spacing": "도메인 글자 사이 공백", "enclosed_alnum": "원·괄호 숫자(ⓞ①⑵)",
        "punct_variant": "대시·쉼표를 다른 문자권 부호로 바꿈(―﹣ ، ˏ)",
        "jamo_homoglyph": "자모로 영문자 바꾸기(TㅇP, ㄹr인)", "smallcaps": "작은 대문자(ʜᴏɴɢʙᴏ)",
        "enclosed_hangul": "원 한글로 음절 바꾸기(㉸톡)", "jamo_inword": "낱말 속 홀자음(텔ㄹ그ㄹ)", "jamo_abbrev": "초성 줄임(ㅌㅌ사이트)", "same_color": "글자색과 바탕색을 같게",
        "spelling_variant": "키워드 일부러 틀리게 쓰기(캬톡·텔래그램·비아그랴)"}

# 구분자에 자모 ㅡ 도 넣는다 (Oloㅡ8359 O6611 꼴, 2026-10-04)
PHONE = re.compile(r"(?<![\w])[0oOⓞ⓪０][\W_ㅡ]{0,3}[1lI①１][\W_ㅡ]{0,3}[0oOⓞ⓪０](?:[\W_ㅡ]{0,3}[\doOlI０-９\u2460-\u24ff]){7,8}")
TOKEN = re.compile(r"\S[^\n]{0,14}?(?:[.。．,]\s*[CcＣｃ]\s*[OoＯｏ]\s*[MmＭｍ]|[.。．]\s*[xｘ][yｙ][zｚ]|닷\s*CoM|쩜\s*컴)"
                   r"|[ㅋ캬카까][ㅑㅏ]?\s?[ㅏ]?톡\s*:?\s*[A-Za-z0-9 ]{3,}", re.I)
PHONE_HEAD = re.compile(r"[0oOⓞ⓪０][\W_]{0,3}[1lI①１][\W_]{0,3}[0oOⓞ⓪０]")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")

LOCATE = r"""
([path, text]) => {
  for (const e of [document.documentElement, document.body]) e.style.setProperty('display', 'block', 'important');
  const norm = s => s.replace(/\s+/g, ' ').trim();
  const own = el => { let s = ''; for (const n of el.childNodes) if (n.nodeType === 3) s += n.nodeValue; return s; };
  const want = norm(text).slice(0, 120);
  const el = [...document.body.querySelectorAll('*')].find(e => norm(own(e)).startsWith(want));
  if (!el) return null;
  let node = el.cloneNode(true), cur = el;
  for (let i = 0; i < 3 && cur.parentElement && cur.parentElement !== document.body; i++) {
    cur = cur.parentElement; const sh = cur.cloneNode(false); sh.removeAttribute('style'); sh.appendChild(node); node = sh;
  }
  node.querySelectorAll('script,style,img,svg,iframe').forEach(n => n.remove());
  // 텍스트 노드 원문 (공백 정리 전)
  const nodes = []; for (const n of el.childNodes) if (n.nodeType === 3 && n.nodeValue.trim()) nodes.push(n.nodeValue);
  return { html: node.outerHTML, nodes };
}
"""
SEL = r"""
() => {
  const el = document.body.querySelector('[data-combo-target]');
  el.removeAttribute('data-combo-target');
  const seg = e => e.tagName.toLowerCase() + (e.id ? '#' + CSS.escape(e.id) : '') + [...e.classList].slice(0, 2).map(c => '.' + CSS.escape(c)).join('');
  const nth = e => { let i = 1; for (let p = e.previousElementSibling; p; p = p.previousElementSibling) if (p.tagName === e.tagName) i++; return `:nth-of-type(${i})`; };
  for (const useNth of [false, true]) {
    const parts = [];
    for (let e = el; e && e !== document.body; e = e.parentElement) {
      parts.unshift(seg(e) + (useNth ? nth(e) : ''));
      const s = parts.join(' > '); const m = document.querySelectorAll(s);
      if (m.length === 1 && m[0] === el) return { sel: s, html: document.body.innerHTML };
    }
  }
  return null;
}
"""


def mask(s: str) -> tuple[str, bool]:
    out, hit = s, False
    for m in list(PHONE.finditer(s)):
        tok = m.group(0)
        # 앞 3자리(010 꼴, 난독화 모양 포함)만 남기고 나머지 숫자는 X
        keep = PHONE_HEAD.match(tok).group(0)
        rest = re.sub(r"[\doOlI０-９\u2460-\u24ff]", "X", tok[len(keep):])
        out = out.replace(tok, keep + rest)
        hit = True
    if EMAIL.search(out):
        out, hit = EMAIL.sub("[email]", out), True
    return out, hit


def main(analysis: str, out: str) -> None:
    rows = json.loads(Path(analysis).read_text(encoding="utf-8"))
    by_key, seen_text = defaultdict(list), set()
    for r in rows:
        feats = sorted(set(r["features"]) - IGNORE)
        if len(feats) < 2:
            continue
        key_text = re.sub(r"\s+", " ", r["text"])[:200]
        if key_text in seen_text:
            continue
        seen_text.add(key_text)
        host = urlsplit(r["url"]).netloc
        by_key[(host, tuple(feats))].append(r)
    picked = [r for k in sorted(by_key) for r in by_key[k][:PER_KEY]]

    items, seen_ev = [], set()
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        ctx = b.new_context(java_script_enabled=False)
        ctx.route("**/*", lambda rt: rt.abort())
        pg = ctx.new_page()
        for r in picked:
            pg.set_content(Path(r["file"]).read_bytes().decode("utf-8", "replace"), wait_until="domcontentloaded")
            got = pg.evaluate(LOCATE, [r["path"], r["text"]])
            if not got:
                continue
            # evidence: 특징이 가장 많이 드러나는 텍스트 노드 원문. 특징도 이 원문(가리기 전)으로 다시 센다
            import analyze_obf as A  # noqa: E402
            ev = max(got["nodes"], key=lambda n: (len(set(A.features(n)) - IGNORE), len(n))).strip()
            feats = sorted(set(A.features(ev)) - IGNORE)
            host = urlsplit(r["url"]).netloc
            if len(feats) < 2 or not re.search("[가-힣]", ev):  # 한글 없는 것(외국어 스팸·인코딩 깨짐)은 대상 아님
                continue
            # evidence 텍스트 자체에 불법광고 어휘가 있어야 한다 (요소 전체가 아니라). 정부 문서 표 기호 같은 오탐 방지
            # 「급전」「텔레」처럼 공백을 지우면 일반 문장에도 생기는 약한 어휘는 빼고, 뜻이 분명한 어휘만 본다
            if len(ev) > 5000 or not STRONG.search(A.loose(ev)):
                continue
            # 중복 기준: 위장된 도메인·연락처 토큰 (같은 토큰이면 같은 변형, 앞뒤 문장만 다른 것은 버린다)
            m = TOKEN.search(ev)
            key = (host, m.group(0).strip() if m else ev[-40:])
            if key in seen_ev:
                continue
            seen_ev.add(key)
            html, m1 = mask(got["html"])
            ev, m2 = mask(ev)
            # 가리면 번호 속 바꿔치기(5８l5 의 l) 흔적도 X 가 된다. 저장본에 실제로 보이는 수법만 남기도록 가린 뒤 다시 센다
            feats = sorted(set(A.features(ev)) - IGNORE)
            if len(feats) < 2:
                continue
            # 조각 안에서 대상 표시 -> 유일 선택자
            pg.set_content(f"<!doctype html><html><body>{html}</body></html>")
            ok = pg.evaluate("""(ev) => { const norm = s => s.replace(/\\s+/g,' ').trim();
                const el = [...document.body.querySelectorAll('*')].reverse().find(e => [...e.childNodes].some(n => n.nodeType===3 && n.nodeValue.trim() === ev));
                if (!el) return false; el.setAttribute('data-combo-target',''); return true; }""", ev)
            if not ok:
                continue
            s = pg.evaluate(SEL)
            if not s:
                continue
            codes = sorted({OFFICIAL[f] for f in feats if f in OFFICIAL})
            etcs = sorted({ETC_NAME[f] for f in feats if f in ETC_NAME})
            items.append({
                "id": f"CB-{len(items) + 1:03d}", "category": "COMBO", "subtype": "+".join(feats),
                "html": s["html"], "css": "", "evidence_text": ev, "expected_location": s["sel"],
                "is_positive": True, "techniques": feats, "label_codes": codes, "extra_findings": etcs,
                "source": f"실측: {r['url']} (2026-10-03 수집, JS 끄고 원문 렌더링)",
                "notes": " · ".join(DESC[f] for f in feats) + (". 전화번호·이메일 가림(난독화 모양은 유지)" if (m1 or m2) else ""),
            })
        b.close()
    Path(out).write_text(yaml.safe_dump(items, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
    from collections import Counter
    print(len(items), "개")
    print(Counter(urlsplit(i["source"].split(" ")[1]).netloc for i in items))
    print(Counter(i["subtype"] for i in items))


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "analyze"))
    main(*sys.argv[1:3])
