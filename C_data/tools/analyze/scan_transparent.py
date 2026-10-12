"""저장한 원문을 다시 렌더링해 TRANSPARENT(투명 텍스트) 후보를 찾는다.

요강 정의: 배경색과 같은 글자색, opacity:0, color:transparent 등으로 한 시각적 은닉.
앞선 검사들은 CSS 속성 값만 봤다. 이 검사기는 렌더링한 뒤 글자마다 다음을 잰다.
  - 조상까지 곱한 실효 opacity
  - 글자색(-webkit-text-fill-color 포함)의 알파
  - 글자색과 실제 바탕색의 WCAG 대비비. 바탕은 조상을 따라 올라가며 처음 칠해진 색을 쓰고,
    없으면 흰색으로 본다. 바탕 그림(background-image)을 만나면 판정 불가로 표시한다

display:none · visibility:hidden · 화면 밖 요소는 OFFSCREEN 몫이라 뺀다.
JS 는 끄고, 문서 요청에는 저장본을 돌려주고, 스타일시트는 미리 받아 둔 사본(data/raw/etc/css)이
있으면 그걸 돌려준다. 그 밖의 네트워크 요청은 전부 막는다.

사용: python tools/analyze/scan_transparent.py 출력.jsonl @목록.lst
      (목록은 한 줄에 html 하나, 같은 이름의 .json 에 url 이 있으면 그 주소로 띄운다)
"""
import json
import re
import sys
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
CSS_DIR = ROOT / "data" / "raw" / "etc" / "css"

# 사전에서 광고 판정에 쓰는 분류만 쓴다(약한 어휘·화이트리스트 제외)
_lex = yaml.safe_load((ROOT / "data" / "lexicon" / "seed.yaml").read_text(encoding="utf-8"))
_terms = sorted({t["term"] for t in _lex if t["category"] in ("gambling_core", "gambling_lure", "adult")},
                key=len, reverse=True)
EXTRA = ["카지노", "바카라", "토토", "슬롯", "먹튀", "놀이터", "꽁머니", "첫충", "가입코드", "룰렛",
         "베팅", "배팅", "홀덤", "파워볼", "비아그라", "시알리스", "레비트라", "대출", "구글찌라시", "흥신소", "출장안마", "선불유심",
         "casino", "betting", "viagra", "cialis", "escort", "porn", "slot", "toto"]
AD = "(" + "|".join(re.escape(t) for t in _terms + EXTRA) + ")"

JS = r"""
(ad) => {
  const re = new RegExp(ad, 'i');
  const SKIP = new Set(['SCRIPT','STYLE','NOSCRIPT','TEMPLATE','TEXTAREA','OPTION','SELECT','TITLE','svg','SVG']);
  const parse = (c) => {
    if (!c) return null;
    if (c === 'transparent') return [0,0,0,0];
    const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return null;
    const p = m[1].split(/[\s,\/]+/).filter(Boolean).map(Number);
    return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1];
  };
  const lum = (c) => { const f = v => { v /= 255; return v <= 0.03928 ? v/12.92 : Math.pow((v+0.055)/1.055, 2.4); };
                       return 0.2126*f(c[0]) + 0.7152*f(c[1]) + 0.0722*f(c[2]); };
  const blend = (fg, bg) => [0,1,2].map(i => fg[i]*fg[3] + bg[i]*(1-fg[3]));
  const path = (el) => { const a = []; for (let e = el; e && e.nodeType === 1 && a.length < 6; e = e.parentElement) {
      let s = e.tagName.toLowerCase(); if (e.id) s += '#' + e.id;
      else if (typeof e.className === 'string' && e.className.trim()) s += '.' + e.className.trim().split(/\s+/).join('.');
      a.unshift(s); } return a.join(' > '); };
  const out = [];
  let n = 0;
  for (const el of document.body ? document.body.querySelectorAll('*') : []) {
    if (SKIP.has(el.tagName)) continue;
    let own = '';
    for (const t of el.childNodes) if (t.nodeType === 3) own += t.nodeValue;
    own = own.replace(/\s+/g, ' ').trim();
    if (own.length < 2) continue;
    n++;
    if (!el.checkVisibility({checkVisibilityCSS: true})) continue;          // display:none · visibility:hidden
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1 || r.right < 0 || r.bottom < 0) continue; // 크기 0 · 화면 밖
    const cs = getComputedStyle(el);
    let op = 1;
    for (let a = el; a && a.nodeType === 1; a = a.parentElement) op *= parseFloat(getComputedStyle(a).opacity);
    const fill = parse(cs.webkitTextFillColor) || parse(cs.color);
    if (!fill) continue;
    let bg = null, bgImg = false;
    for (let a = el; a && a.nodeType === 1; a = a.parentElement) {
      const s = getComputedStyle(a);
      if (s.backgroundImage && s.backgroundImage !== 'none') { bgImg = true; break; }
      const b = parse(s.backgroundColor);
      if (b && b[3] > 0.5) { bg = b; break; }
    }
    const bgc = bg || [255,255,255,1];
    const fg = blend(fill, bgc);
    const L1 = lum(fg), L2 = lum(bgc);
    const contrast = (Math.max(L1,L2)+0.05) / (Math.min(L1,L2)+0.05);
    const flags = [];
    if (op <= 0.1) flags.push('opacity');
    if (fill[3] <= 0.1) flags.push('color_alpha');
    if (contrast <= 1.2 && fill[3] > 0.1 && op > 0.1) flags.push(bgImg ? 'same_color_bgimg' : 'same_color');
    if (!flags.length) continue;
    out.push({flags, op: +op.toFixed(3), color: cs.color, fill: cs.webkitTextFillColor, bg: bg ? `rgba(${bg.join(',')})` : (bgImg ? 'image' : 'default-white'),
              contrast: +contrast.toFixed(3), fs: cs.fontSize, path: path(el), ad: (own.match(re) || [null])[0], text: own.slice(0, 200)});
  }
  return {n, out};
}
"""


def css_map() -> dict:
    m = {}
    for j in CSS_DIR.glob("*_browser.json"):
        try:
            u = json.loads(j.read_text(encoding="utf-8")).get("url")
        except Exception:  # noqa: BLE001
            continue
        h = j.with_suffix(".html")
        if u and h.exists():
            m[u] = h
    return m


def main(out: str, files: list[str]) -> None:
    cmap = css_map()
    done = set()
    op = Path(out)
    if op.exists():
        for line in op.read_text(encoding="utf-8").splitlines():
            done.add(json.loads(line)["file"])
    with sync_playwright() as p, op.open("a", encoding="utf-8") as fo:
        b = p.chromium.launch(channel="msedge")
        ctx = b.new_context(java_script_enabled=False, viewport={"width": 1280, "height": 900})
        for f in files:
            if f in done:
                continue
            fp = Path(f)
            meta_p = fp.with_suffix(".json")
            url = ""
            if meta_p.exists():
                try:
                    url = json.loads(meta_p.read_text(encoding="utf-8")).get("url", "")
                except Exception:  # noqa: BLE001
                    pass
            raw = fp.read_bytes().decode("utf-8", "replace")
            raw = re.sub(r"<meta[^>]+http-equiv=[\"']?refresh[^>]*>", "", raw, flags=re.I)
            used_css = []

            def handle(rt, _req=None, raw=raw, used=used_css):
                rq = rt.request
                if rq.resource_type == "document" and rq.frame == rq.frame.page.main_frame:
                    return rt.fulfill(status=200, body=raw, content_type="text/html; charset=utf-8")
                if rq.resource_type == "stylesheet" and rq.url in cmap:
                    used.append(rq.url)
                    return rt.fulfill(status=200, body=cmap[rq.url].read_bytes(), content_type="text/css")
                return rt.abort()

            pg = ctx.new_page()
            pg.set_default_timeout(15000)
            rec = {"file": f, "url": url}
            try:
                pg.route("**/*", handle)
                if url.startswith("http"):
                    try:
                        pg.goto(url, wait_until="load", timeout=15000)
                    except Exception:  # noqa: BLE001
                        pg.set_content(raw, wait_until="domcontentloaded")
                else:
                    pg.set_content(raw, wait_until="domcontentloaded")
                r = pg.evaluate(JS, AD)
                rec.update(n_text=r["n"], css=len(used_css), hits=r["out"])
            except Exception as e:  # noqa: BLE001
                rec["error"] = f"{type(e).__name__}: {str(e)[:120]}"
            finally:
                try:
                    pg.close()
                except Exception:  # noqa: BLE001
                    pass
            fo.write(json.dumps(rec, ensure_ascii=False) + "\n")
            fo.flush()
        b.close()


if __name__ == "__main__":
    args = sys.argv[2:]
    files = []
    for a in args:
        if a.startswith("@"):
            files += [l.strip() for l in Path(a[1:]).read_text(encoding="utf-8").splitlines() if l.strip()]
        else:
            files.append(a)
    main(sys.argv[1], files)
