"""저장한 실제 페이지 원문에서 ETC 5종 실사례를 찾아 샘플 후보로 잘라 낸다 (생성 없음).

zero_width    광고 문구 텍스트에 보이지 않는 문자(제로폭·소프트하이픈·한글 채움 문자 등)가 들어 있음
link_cloaking 광고 글(감싼 블록에 광고 어휘) 안의 외부 링크인데, 앵커 텍스트에는 광고 어휘·주소가 없음. 메뉴·푸터 제외
css_content   ::before/::after 계산 content 에 광고 어휘
meta_cloaking head 의 title·meta·JSON-LD 에 광고 어휘가 있는데 화면에 보이는 본문에는 그 어휘가 하나도 없음
encoding      원문 html 에 숫자 엔티티·base64 로 적힌 광고 문구 (DOM 에서는 풀려 보임)

렌더링은 JS 끔 · 네트워크 전부 차단. body style="display:none" 은 풀고 판정한다.
사용: python analyze_etc.py out.json file.html [...]
"""
import base64
import json
import re
import sys
import unicodedata
from html import unescape
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

AD = (r"카지노|바카라|토토|토지노|슬롯|먹튀|놀이터|꽁머니|첫충|매충|가입코드|룰렛|베팅|배팅|홀덤|파워볼|에볼루션|바둑이|릴게임|야마토|"
      r"바다이야기|섯다|맞고게임|비아그라|시알리스|최음제|흥분제|레비트라|조건만남|출장안마|작업대출|내구제|대포통장|대포폰|"
      r"casino|baccarat|toto|slot")
INVIS = "​‌‍‎‏⁠⁡⁢⁣⁤﻿­͏ᅟᅠㅤﾠ᠎"

JS = r"""
([AD, INVIS]) => {
  for (const e of [document.documentElement, document.body]) {
    const cs = getComputedStyle(e);
    if (cs.display === 'none' || cs.visibility === 'hidden') { e.style.setProperty('display','block','important'); e.style.setProperty('visibility','visible','important'); }
  }
  const ad = new RegExp(AD, 'i');
  const invisRe = new RegExp('[' + INVIS + ']');
  // \W 는 JS 에서 한글까지 지우므로 쓰지 않는다. 공백·문장부호·기호만 뺀다
  const loose = s => s.normalize('NFKC').replace(new RegExp('[' + INVIS + ']', 'g'), '').replace(/[\s\p{P}\p{S}_]+/gu, '');
  const MAJOR = /(^|\.)(coupang(corp)?\.com|chosun(online)?\.com|naver\.(com|me)|daum\.net|kakao\.com|google\.[a-z.]+|youtube\.com|youtu\.be|facebook\.com|instagram\.com|twitter\.com|x\.com|microsoft\.com|mozilla\.org|apple\.com|[a-z0-9-]+\.(go|ac|or|re|hs|ms|es|sc)\.kr|baidu\.com|samsung\.com|taboola\.com|juvis\.co\.kr|kogl\.or\.kr)$/i;
  const own = el => { let s = ''; for (const n of el.childNodes) if (n.nodeType === 3) s += n.nodeValue; return s; };
  const out = [];
  let k = 0;
  const mark = (el, kind, extra) => { el.setAttribute('data-etc-k', String(k)); out.push(Object.assign({k: k++, kind}, extra)); };
  for (const el of document.body.querySelectorAll('*')) {
    if (['SCRIPT','STYLE','NOSCRIPT'].includes(el.tagName)) continue;
    const t = own(el);
    // zero_width
    if (t.trim() && invisRe.test(t) && ad.test(loose(t))) {
      const nodes = [...el.childNodes].filter(n => n.nodeType === 3 && invisRe.test(n.nodeValue)).map(n => n.nodeValue);
      mark(el, 'zero_width', {ev: nodes[0].trim(), chars: [...new Set([...nodes.join('')].filter(c => invisRe.test(c)).map(c => 'U+' + c.codePointAt(0).toString(16).toUpperCase().padStart(4, '0')))]});
    }
    // link_cloaking
    if (el.tagName === 'A' && /^https?:/i.test(el.getAttribute('href') || '')) {
      const href = el.getAttribute('href');
      const at = el.textContent.trim();
      const host = (() => { try { return new URL(href).host; } catch (e) { return ''; } })();
      if (at && host && host !== location.host && !MAJOR.test(host) && !ad.test(loose(at)) && !/https?:|www\.|\.(com|net|kr|top|xyz|org)\b/i.test(at)
          && !el.closest('header,footer,nav,#gnb,.gnb,#lnb,.lnb,#footer,.footer,#header,.header,.sns,.family')) {
        let blk = el.parentElement, ok = false;
        for (let i = 0; i < 4 && blk && blk !== document.body; i++, blk = blk.parentElement) {
          if (ad.test(loose(blk.textContent || ''))) { ok = true; break; }
        }
        if (ok) mark(el, 'link_cloaking', {ev: href, anchor: at});
      }
    }
    // css_content
    for (const pseudo of ['::before', '::after']) {
      const c = getComputedStyle(el, pseudo).content;
      if (c && c !== 'none' && c !== 'normal' && ad.test(loose(c))) { mark(el, 'css_content', {ev: c, pseudo}); break; }
    }
  }
  // meta_cloaking
  const head = [];
  const tt = document.querySelector('head > title'); if (tt && ad.test(loose(tt.textContent))) head.push(['head > title', tt.textContent.trim()]);
  for (const sel of ['meta[name="description"]','meta[property="og:title"]','meta[property="og:description"]','meta[name="keywords"]','meta[name="twitter:title"]']) {
    const m = document.querySelector(sel); if (m && ad.test(loose(m.getAttribute('content') || ''))) head.push([sel, m.getAttribute('content')]);
  }
  for (const s of document.querySelectorAll('script[type="application/ld+json"]')) if (ad.test(loose(s.textContent))) head.push(['script[type="application/ld+json"]', s.textContent.trim().slice(0, 600)]);
  const bodyText = loose(document.body.innerText || '');
  const bodyAd = bodyText.match(new RegExp(AD, 'gi')) || [];
  return {items: out, head, bodyAdCount: bodyAd.length, host: location.host};
}
"""

CUT = r"""
(k) => {
  const el = document.querySelector(`[data-etc-k="${k}"]`);
  let node = el.cloneNode(true), cur = el;
  for (let i = 0; i < 3 && cur.parentElement && cur.parentElement !== document.body; i++) {
    cur = cur.parentElement; const sh = cur.cloneNode(false); sh.removeAttribute('style'); sh.appendChild(node); node = sh;
  }
  node.querySelectorAll('script,style,img,svg,iframe').forEach(n => n.remove());
  node.querySelectorAll('[data-etc-k]').forEach(n => { if (n.getAttribute('data-etc-k') !== String(k)) n.removeAttribute('data-etc-k'); });
  return node.outerHTML;
}
"""
SEL = r"""
() => {
  const el = document.querySelector('[data-etc-k]'); el.removeAttribute('data-etc-k');
  const seg = e => e.tagName.toLowerCase() + (e.id ? '#' + CSS.escape(e.id) : '') + [...e.classList].slice(0, 2).map(c => '.' + CSS.escape(c)).join('');
  const nth = e => { let i = 1; for (let p = e.previousElementSibling; p; p = p.previousElementSibling) if (p.tagName === e.tagName) i++; return `:nth-of-type(${i})`; };
  for (const useNth of [false, true]) { const parts = [];
    for (let e = el; e && e !== document.body; e = e.parentElement) { parts.unshift(seg(e) + (useNth ? nth(e) : ''));
      const s = parts.join(' > '); const m = document.querySelectorAll(s); if (m.length === 1 && m[0] === el) return {sel: s, html: document.body.innerHTML}; } }
  return null;
}
"""


def entity_hits(raw: str) -> list[tuple[str, str]]:
    """원문에서 엔티티 연속·base64 를 풀어 광고 어휘가 나오는 것."""
    hits = []
    for m in re.finditer(r"(?:&#(?:x[0-9a-fA-F]{2,6}|\d{2,7});\s*){2,}", raw):
        dec = unescape(m.group(0))
        if re.search(AD, unicodedata.normalize("NFKC", dec), re.I):
            hits.append((m.group(0), dec))
    for m in re.finditer(r"(?:atob\(\s*['\"]|base64,)([A-Za-z0-9+/=]{16,})", raw):
        try:
            dec = base64.b64decode(m.group(1) + "===").decode("utf-8", "ignore")
        except Exception:  # noqa: BLE001
            continue
        if re.search(AD, dec, re.I):
            hits.append((m.group(1), dec[:200]))
    return hits


def main(out: str, files: list[str]) -> None:
    res = []
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        ctx = b.new_context(java_script_enabled=False, viewport={"width": 1280, "height": 900})
        def _abort(rt):
            try:
                rt.abort()
            except Exception:  # noqa: BLE001  페이지 쪽 가로채기가 이미 응답한 요청
                pass
        ctx.route("**/*", _abort)
        pg = ctx.new_page()
        for f in files:
            fp = Path(f)
            meta = json.loads(fp.with_suffix(".json").read_text(encoding="utf-8")) if fp.with_suffix(".json").exists() else {}
            url = meta.get("url", "")
            raw = fp.read_bytes().decode("utf-8", "replace")
            # 자동 이동(meta refresh)이 렌더링 중 페이지를 바꾸지 않도록 그 태그만 뺀다
            raw_view = re.sub(r"<meta[^>]+http-equiv=[\"']?refresh[^>]*>", "", raw, flags=re.I)
            def run(page, keep_route: bool):
                # location.host 가 원래 호스트가 되도록 원래 URL 로 띄운다 (응답은 저장본, 네트워크는 막힘)
                # 주소 문자열 비교는 한글 URL 인코딩 차이로 어긋나므로, 문서 요청이면 저장본을 돌려주고 나머지는 막는다
                def _serve(rt):
                    try:
                        if rt.request.resource_type == "document":
                            rt.fulfill(status=200, body=raw_view, content_type="text/html; charset=utf-8")
                        else:
                            rt.abort()
                    except Exception:  # noqa: BLE001  이미 처리된 요청
                        pass
                page.route("**/*", _serve)
                try:
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=15000)
                    except Exception:  # noqa: BLE001
                        page.set_content(raw_view, wait_until="domcontentloaded")
                finally:
                    if not keep_route:
                        try:
                            page.unroute("**/*")
                        except Exception:  # noqa: BLE001
                            pass
                rr = page.evaluate(JS, [AD, INVIS])
                return rr, {it["k"]: page.evaluate(CUT, it["k"]) for it in rr["items"]}

            try:
                r, snips = run(pg, keep_route=False)
            except Exception:  # noqa: BLE001
                # 한 탭에서 가로채기를 걸었다 풀기를 반복하다 상태가 꼬인 경우: 새 탭에서 가로채기를 유지한 채 한 번 더
                try:
                    pg.close()
                except Exception:  # noqa: BLE001
                    pass
                pg = ctx.new_page()
                fpg = ctx.new_page()
                try:
                    r, snips = run(fpg, keep_route=True)
                except Exception as e:  # noqa: BLE001
                    print("skip", fp.name, type(e).__name__)
                    continue
                finally:
                    try:
                        fpg.close()
                    except Exception:  # noqa: BLE001
                        pass
            for it in r["items"]:
                snip = snips[it["k"]]
                res.append({"file": str(fp), "url": url, "kind": it["kind"], "snippet": snip,
                            **{k: v for k, v in it.items() if k not in ("k", "kind")}})
            if r["head"] and r["bodyAdCount"] == 0:
                for sel, val in r["head"]:
                    res.append({"file": str(fp), "url": url, "kind": "meta_cloaking", "ev": val, "loc": sel,
                                "snippet": None})
            for enc, dec in entity_hits(raw):
                res.append({"file": str(fp), "url": url, "kind": "encoding", "ev": enc, "decoded": dec, "snippet": None})
        # 조각 안 유일 선택자: 앞에서 가로채기로 상태가 꼬였을 수 있으니 새 탭에서, 항목 하나가 실패해도 계속
        sp = ctx.new_page()
        for x in res:
            if x["snippet"]:
                try:
                    sp.set_content(f"<!doctype html><html><body>{x['snippet']}</body></html>")
                    s = sp.evaluate(SEL)
                except Exception:  # noqa: BLE001
                    try:
                        sp.close()
                    except Exception:  # noqa: BLE001
                        pass
                    sp = ctx.new_page()
                    s = None
                x["loc"], x["snippet"] = (s["sel"], s["html"]) if s else (None, x["snippet"])
        b.close()
    Path(out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print(Counter(x["kind"] for x in res))
    print(Counter((x["kind"], urlsplit(x["url"]).netloc) for x in res).most_common(40))


def expand(args: list[str]) -> list[str]:
    """@목록.txt 를 받으면 그 안의 경로들로 펼친다 (Windows 명령줄 길이 제한 회피)."""
    out = []
    for a in args:
        out += Path(a[1:]).read_text(encoding="utf-8-sig").splitlines() if a.startswith("@") else [a]
    return out


if __name__ == "__main__":
    main(sys.argv[1], expand(sys.argv[2:]))
