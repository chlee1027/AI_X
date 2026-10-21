"""추가 유형 탐지 (10-20, 진행보고서 7-50절). 모집요강 붙임1·4: 주요 4종 밖 유형은 result_extra.json 에 technique "ETC",
유형 이름은 extra_finding 에 적는다. 유형 이름은 팀 데이터셋(dev_data/etc)의 다섯 갈래를 따른다.

  ZERO_WIDTH    : 요소 자기 글자 안, 글자 사이에 보이지 않는 글자(U+00AD·U+200B~U+200D·U+2060·U+FEFF)를 끼운 광고 문구
  ENCODING      : 광고 문구를 링크 주소(또는 글자)의 퍼센트 인코딩 안에만 둔 것, 또는 원문 HTML 에서 숫자 문자 참조(&#53076; 꼴)로만
                  적은 것(브라우저가 풀어 그리므로 DOM 에는 안 남는다. 응답 원문으로 찾는다)
  META_CLOAKING : 광고 문구를 head 의 meta(description·og·twitter)·title 에만 둔 것
  CSS_CONTENT   : 광고 문구를 CSS ::before·::after 의 content 에만 둔 것
  LINK_CLOAKING : 정상 문구 링크의 주소가 단축 주소·퓨니코드·의심 최상위 도메인·무작위 꼴 호스트인 것
광고인지는 4종과 같은 광고 여부 판정기(글자)로 본다. 문턱 AD_THR 은 측정 전에 정했다(7-50절).
"""
import html as _html
import re
import unicodedata
from urllib.parse import unquote_plus, urlparse

AD_THR = 0.5
TYPES = ("ZERO_WIDTH", "ENCODING", "META_CLOAKING", "CSS_CONTENT", "LINK_CLOAKING")
ZW = re.compile("[­​-‍⁠﻿]")
# 10-21(진행보고서 7-77절): 한글 음절 사이의 보이지 않는 글자는 정상 데이터(음성 2.1만 줄·정상 사이트 66만 줄)에서 0 -> 광고 점수와 상관없이 낸다
HZW = re.compile("[가-힣][­​-‍⁠﻿]+[가-힣]")
SHORT = {"bit.ly", "t.ly", "tinyurl.com", "cutt.ly", "goo.gl", "is.gd", "han.gl", "me2.kr", "url.kr", "vo.la", "buly.kr",
         "abit.ly", "t.co", "ow.ly", "rebrand.ly", "shorturl.at", "tiny.cc", "c11.kr", "zrr.kr", "lrl.kr"}
BAD_TLD = {"top", "xyz", "club", "click", "icu", "vip", "bet", "casino", "poker", "win", "live", "fun", "buzz", "monster", "cyou", "sbs", "cfd"}
RAND_HOST = re.compile(r"(^|\.)[a-z]{1,6}\d{2,}[a-z\d]*\.[a-z]{2,}$")
# 10-20(7-52절): 공공 사이트도 단축 주소·숫자 도메인(예: 전화번호 도메인)을 정상으로 쓴다. 링크 글이 「바로가기·접속」 같은
# 행동 유도 문구일 때만 LINK_CLOAKING 으로 본다(도박 게이트 링크는 이름 대신 이동만 권한다).
CTA = re.compile(r"바로\s*가기|접속|입장|이동|시작하기|클릭|링크|로그인|회원\s*가입|가입하기|주소|우회|여기|click|enter|login|join|go\b", re.I)
PCT_RUN = re.compile(r"(?:%[0-9A-Fa-f]{2}|\+)+")

JS = r"""() => {
  const esc = (s) => (window.CSS && CSS.escape) ? CSS.escape(s) : s;
  const step = (el) => { let s = el.tagName.toLowerCase();
    const cls = Array.from(el.classList).filter(c => /^[A-Za-z_-][\w-]*$/.test(c));
    if (cls.length) s += '.' + cls.map(esc).join('.');
    const p = el.parentElement;
    if (p) { const same = Array.from(p.children).filter(c => c.tagName === el.tagName);
      if (same.length > 1 && !cls.length) s += ':nth-of-type(' + (same.indexOf(el) + 1) + ')';
      else if (same.length > 1) { const sameCls = same.filter(c => c.matches(s)); if (sameCls.length > 1) s += ':nth-of-type(' + (same.indexOf(el) + 1) + ')'; } }
    return s; };
  const sel = (el) => { let parts = [], e = el;
    while (e && e !== document.documentElement) { parts.unshift(step(e));
      const q = parts.join(' > '); try { if (document.querySelectorAll(q).length === 1) return q; } catch (x) {}
      e = e.parentElement; }
    return parts.join(' > '); };
  const out = [];
  const SKIP = new Set(['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEMPLATE']);
  const ZWS = /\S[­​-‍⁠﻿]+\S/;
  const PCT = /(?:%[89A-Fa-f][0-9A-Fa-f]){6,}/;
  for (const el of (document.body ? document.body.querySelectorAll('*') : [])) {
    if (SKIP.has(el.tagName)) continue;
    let own = '';
    for (const n of el.childNodes) if (n.nodeType === 3) own += n.nodeValue;
    if (ZWS.test(own)) out.push({type: 'ZERO_WIDTH', sel: sel(el), text: (el.textContent || '').trim().slice(0, 400)});
    if (PCT.test(own)) out.push({type: 'ENCODING', sel: sel(el), text: own.trim().slice(0, 600), raw: own.trim().slice(0, 300)});
    if (el.tagName === 'A' && el.getAttribute('href')) {
      const h = el.getAttribute('href');
      if (PCT.test(h)) out.push({type: 'ENCODING', sel: sel(el), text: h.slice(0, 1500), raw: h.slice(0, 300)});
      if (/^https?:/i.test(el.href)) out.push({type: 'LINK', sel: sel(el), text: (el.textContent || '').trim().slice(0, 200), href: el.href});
    }
  }
  const metas = ['meta[name="description"]', 'meta[property="og:description"]', 'meta[property="og:title"]',
                 'meta[name="twitter:title"]', 'meta[name="twitter:description"]', 'meta[name="keywords"]'];
  for (const q of metas) { const m = document.querySelector(q);
    if (m && m.getAttribute('content')) out.push({type: 'META_CLOAKING', sel: q, text: m.getAttribute('content').slice(0, 400)}); }
  const t = document.querySelector('head > title');
  if (t && t.textContent.trim()) out.push({type: 'META_CLOAKING', sel: 'head > title', text: t.textContent.trim().slice(0, 400)});
  const rules = [];
  const walk = (rs) => { for (const r of rs) { if (r.cssRules) { try { walk(r.cssRules); } catch (x) {} }
    if (r.selectorText && r.style && r.style.content) rules.push(r); } };
  for (const sh of document.styleSheets) { try { walk(sh.cssRules); } catch (x) {} }
  for (const r of rules) {
    if (!/::?(before|after)/i.test(r.selectorText)) continue;
    let c = r.style.content.trim();
    if (!/^["']/.test(c)) continue;
    c = c.slice(1, -1).replace(/\\[0-9a-fA-F]{1,6}\s?/g, '').trim();
    if (c.length < 4 || !/[A-Za-z가-힣]/.test(c)) continue;
    for (const part of r.selectorText.split(',')) {
      const base = part.replace(/::?(before|after)/gi, '').trim() || '*';
      let el = null; try { el = document.querySelector(base); } catch (x) {}
      if (el) { out.push({type: 'CSS_CONTENT', sel: sel(el), text: c.slice(0, 400)}); break; }
    }
  }
  return out;
}"""


def collect(frame, prefix=""):
    try:
        items = frame.evaluate(JS)
    except Exception:
        return []
    for it in items:
        it["sel"] = prefix + it["sel"]
    return items


ENT_RUN = re.compile(r"(?:&#x?[0-9A-Fa-f]{2,6};\s*){6,}")
ENT_JS = r"""(texts) => { const out = [];
  for (const el of (document.body ? document.body.querySelectorAll('*') : [])) {
    let own = ''; for (const n of el.childNodes) if (n.nodeType === 3) own += n.nodeValue;
    own = own.replace(/\s+/g, ' ');
    for (let k = 0; k < texts.length; k++) if (texts[k] && own.includes(texts[k])) out.push([k, el]); }
  return out.map(([k, el]) => [k, (() => { const esc = (s) => (window.CSS && CSS.escape) ? CSS.escape(s) : s;
    const step = (el) => { let s = el.tagName.toLowerCase(); const cls = Array.from(el.classList).filter(c => /^[A-Za-z_-][\w-]*$/.test(c));
      if (cls.length) s += '.' + cls.map(esc).join('.'); const p = el.parentElement;
      if (p) { const same = Array.from(p.children).filter(c => c.tagName === el.tagName);
        if (same.length > 1 && !cls.length) s += ':nth-of-type(' + (same.indexOf(el) + 1) + ')';
        else if (same.length > 1) { const sc = same.filter(c => c.matches(s)); if (sc.length > 1) s += ':nth-of-type(' + (same.indexOf(el) + 1) + ')'; } }
      return s; };
    let parts = [], e = el; while (e && e !== document.documentElement) { parts.unshift(step(e)); const q = parts.join(' > ');
      try { if (document.querySelectorAll(q).length === 1) return q; } catch (x) {} e = e.parentElement; } return parts.join(' > '); })()]); }"""


def collect_entities(frame, raw_html, prefix=""):
    """원문 HTML 의 숫자 문자 참조 덩어리(6개 이상)를 풀어, 그 글을 자기 글자로 가진 요소를 찾는다."""
    runs = [m.group(0) for m in ENT_RUN.finditer(raw_html or "")][:50]
    texts = [re.sub(r"\s+", " ", _html.unescape(r)).strip()[:40] for r in runs]
    if not texts:
        return []
    try:
        found = frame.evaluate(ENT_JS, texts)
    except Exception:
        return []
    out, seen = [], set()
    for k, sel in found:
        if sel not in seen:
            seen.add(sel)
            out.append({"type": "ENCODING", "sel": prefix + sel, "text": _html.unescape(runs[k]), "raw": runs[k][:300]})
    return out


def clean(t):
    """이모지·기호·사용자 정의 글자를 띄어쓰기로 바꾼다(글자·숫자와 주소에 쓰는 문장부호만 남김). 광고 점수를 매기기 전에 쓴다."""
    return re.sub(r"\s+", " ", "".join(c if unicodedata.category(c)[0] in "LNZ" or c in "@.:/-_#&%+~" else " " for c in t)).strip()


def _decode(s):
    try:
        return unquote_plus(s)
    except Exception:
        return s


def suspicious_link(href, page_host):
    """다른 호스트로 가는 링크의 주소가 의심 꼴인지(근거 문구 목록). 같은 사이트·공공 도메인은 보지 않는다."""
    h = (urlparse(href).hostname or "").lower()
    if not h or not page_host:
        return []
    ph = page_host.lower().removeprefix("www.")
    if h.removeprefix("www.") == ph or h.endswith("." + ph) or ph.endswith("." + h.removeprefix("www.")):
        return []
    if h.endswith((".go.kr", ".or.kr", ".ac.kr", ".re.kr", ".mil.kr", ".gov", ".edu")):
        return []
    why = []
    if h in SHORT:
        why.append("단축 주소")
    if "xn--" in h:
        why.append("퓨니코드 호스트")
    if h.rsplit(".", 1)[-1] in BAD_TLD:
        why.append("의심 최상위 도메인 ." + h.rsplit(".", 1)[-1])
    if RAND_HOST.search(h):
        why.append("영문자+숫자 무작위 꼴 호스트")
    return why


def judge(items, model, page_url, llm=None):
    """수집한 후보 -> [(유형, 선택자, 근거 글, 광고 점수, [근거])]. model 은 v9 등(model.ad.score 를 쓴다)."""
    rows, meta = [], []
    host = urlparse(page_url).hostname or ""
    for it in items:
        t, why = it["type"], []
        if t == "ZERO_WIDTH":
            text = ZW.sub("", it["text"])
            why = [f"보이지 않는 글자 {len(ZW.findall(it['text']))}개"]
        elif t == "ENCODING":
            # 7-52절: 주소 전체를 점수 매기면 주소 꼴 자체가 광고 단서가 된다. 인코딩된 덩어리를 푼 글만 본다
            text = it["text"] if "&#" in (it.get("raw") or "") else " ".join(_decode(m.group(0)) for m in PCT_RUN.finditer(it["text"]))
            if len(re.findall(r"[^\x00-\x7f]", text)) < 4:
                continue
            why = ["퍼센트 인코딩 안의 광고 문구"]
        elif t == "LINK":
            why = suspicious_link(it.get("href", ""), host)
            if not why or not CTA.search(it["text"]):  # 글 없는 그림 배너 링크는 공공 사이트에 흔해 보지 않는다(7-52절)
                continue
            t, text = "LINK_CLOAKING", it["text"]
        else:
            text = it["text"]
            why = ["head 메타 글"] if t == "META_CLOAKING" else ["CSS content 글"]
        rows.append({"sid": "x", "i": len(rows), "parent": -1, "tag": "a" if t in ("LINK_CLOAKING", "ENCODING") else "p", "text": clean(text), "raw_text": it["text"],
                     "href": it.get("href", ""), "f": {}, "rt": {}, "lab": {}, "t_skip": 0})
        meta.append((t, it["sel"], it.get("raw") or it.get("href") or it["text"], why))
    if not rows:
        return []
    ad = model.ad.score(rows)
    # 10-21(7-77절): API 판이면 광고 점수 문턱 아래 후보를 v2x 판정기에 묻고, 확신하는 「광고」면 낸다
    ai = {}
    if llm is not None and not getattr(llm, "dead", None):
        ask = [(k, {"key": "extra|" + t + "|" + r["text"], "text": r["text"], "how": "추가 유형 " + t, "link": (r.get("href") or "")[:120]})
               for k, ((t, sel, ev, why), a, r) in enumerate(zip(meta, ad, rows)) if a < AD_THR and t != "LINK_CLOAKING" and r["text"].strip()]
        if ask:
            v = llm.verdicts2([it for _, it in ask])
            ai = {k: v[it["key"]] for k, it in ask if it["key"] in v}
    out, seen = [], set()
    for k, ((t, sel, ev, why), a, r) in enumerate(zip(meta, ad, rows)):
        if t == "LINK_CLOAKING":
            ok = a < AD_THR and len(r["text"]) <= 40  # 링크 글이 광고면 4종 쪽(또는 다른 갈래)에서 잡는다
        elif t == "ZERO_WIDTH" and HZW.search(r.get("raw_text", "")):
            ok = True
            why = why + ["한글 음절 사이에 보이지 않는 글자(정상 글에서 안 나옴)"]
        else:
            ok = a >= AD_THR or ai.get(k) == (True, True)
            if a < AD_THR and ok:
                why = why + ["AI 판정: 광고(확신)"]
        if ok and (t, sel) not in seen:
            seen.add((t, sel))
            out.append((t, sel, ev, float(a), why))
    return out


# 10-20(진행보고서 7-58절): 글자 변형 추가 유형. 팀 데이터셋 COMBO 추가 정답(answer_result_extra_combo.json)의 이름을 따른다.
# 광고 점수가 AD_THR 이상인 잎 요소(자식 후보 없음)의 글에만 본다. 한 요소에 여러 유형이 붙을 수 있다(요강 작성 예시도 같은 위치 둘).
SYM_SEP = re.compile(r"[←-⇿─-➿⬀-⯿㈀-㋿■-◿☀-⛿≪≫«»]")
KW_SPACE = re.compile(r"(?<![^\s\[(])(?:[가-힣A-Za-z0-9](?:[  ]+|$)){3,}")
TLD_TOK = re.compile(r"[.。．]\s*([A-Za-zＡ-Ｚａ-ｚ]{2,4})(?![A-Za-z])")


def case_mix(text):
    """도메인 끝(com·net 등)이 대소문자 섞임(예: cOM, coM)이면 참. 모두 소문자·모두 대문자는 정상."""
    for m in TLD_TOK.finditer(text):
        w = unicodedata.normalize("NFKC", m.group(1))
        if w.lower() in ("com", "net", "kr", "org", "top", "xyz", "co") and not (w.islower() or w.isupper()):
            return True
    return False
DOT_SUB = re.compile(r"[A-Za-z0-9가-힣]\s*(?:[。｡．・･∙⋅ㆍ]|쩜|\(dot\)|\[dot\]| dot )\s*(?:com|net|kr|co|org|top|xyz|io|me|shop|site|vip|bet|win|cc)(?![A-Za-z])", re.I)
DOM_SPACE = re.compile(r"[A-Za-z0-9]+\s+[.。]\s*(?:com|net|kr|top|xyz)\b|[A-Za-z0-9]\.\s*[cC]\s+[oO]\s*[mM]\b|\b[cC]\s+[oO][mM]\b", re.I)
KANA = re.compile(r"[぀-ヿ]")


def text_types(text):
    """글 하나 -> [(유형, 근거)]. 광고 여부는 부르는 쪽이 본다."""
    out = []
    if len(SYM_SEP.findall(text)) >= 2:
        out.append(("SYMBOL_SEPARATOR", f"장식 기호 {len(SYM_SEP.findall(text))}개로 낱말 사이를 끊음"))
    m = KW_SPACE.search(text)
    if m and len(m.group(0).split()) >= 3:
        out.append(("KEYWORD_SPACING", "한 글자씩 띄어 쓴 낱말"))
    if case_mix(text):
        out.append(("CASE_MIX", "대소문자를 섞은 주소·낱말"))
    if DOT_SUB.search(text):
        out.append(("DOT_SUBSTITUTION", "도메인 점 자리를 다른 글자로 바꿈"))
    if DOM_SPACE.search(text):
        out.append(("DOMAIN_SPACING", "도메인 안에 띄어쓰기"))
    if KANA.search(text) and len(re.findall(r"[가-힣]", text)) >= 5:
        out.append(("KANA_SEPARATOR", "한글 글 사이에 일본 가나를 끼움"))
    return out


def judge_rows(rows, ad):
    """판정이 끝난 4종 후보 줄(rows, 광고 점수 ad) -> [(유형, 선택자, 근거 글, 점수, [근거])]. scan4.process 가 부른다."""
    kids = {(r["sid"], r["parent"]) for r in rows}
    out = []
    for r, a in zip(rows, ad):
        if a < AD_THR or (r["sid"], r["i"]) in kids:
            continue
        for t, why in text_types(r["text"]):
            out.append((t, r.get("sel", ""), r["text"][:300], float(a), [why]))
    return out
