"""표본을 Edge 로 그려 후보 요소와 화면 특징을 뽑는다(라벨과 무관한 계산, 결과는 cache 에 저장).

페이지 = <style>{css}</style><div id="root">{html}</div>. 표본 스크립트는 돌리지 않고(JS 끔), 네트워크도 막는다.
후보 = #root 아래에서 글자(textContent)가 있는 모든 요소(스크립트·스타일 제외), 표본당 MAX_CAND 개까지.
각 후보의 특징은 브라우저가 계산한 값만 쓴다(요강 붙임1의 투명·화면 밖 정의와 CSS 의미에서 정함, 데이터를 보고 정하지 않음).
정답 위치 선택자는 같은 페이지에서 풀어 후보 번호로 바꾼다(정확히 1개를 가리킬 때만, 아니면 -1).

사용: python render.py <데이터 폴더> <출력 jsonl> [작업자 수]
"""
import json
import sys
from multiprocessing import Pool
from pathlib import Path

from common import load_samples

MAX_CAND = 400

JS = r"""
([maxCand, goldSels]) => {
  const root = document.getElementById('root');
  const all = Array.from(root.querySelectorAll('*'));
  const skip = new Set(['SCRIPT','STYLE','NOSCRIPT','TEMPLATE','HEAD','META','LINK']);
  const docW = Math.max(document.documentElement.scrollWidth, 1280);
  const docH = Math.max(document.documentElement.scrollHeight, 800);
  const pc = (s) => { const m = (s||'').match(/rgba?\(([^)]+)\)/); if (!m) return [0,0,0,1];
    const v = m[1].split(/[ ,\/]+/).filter(x=>x).map(parseFloat); return [v[0]||0, v[1]||0, v[2]||0, v.length>3 ? v[3] : 1]; };
  const lum = (c) => { const f = (x) => { x/=255; return x<=0.03928 ? x/12.92 : Math.pow((x+0.055)/1.055, 2.4); };
    return 0.2126*f(c[0]) + 0.7152*f(c[1]) + 0.0722*f(c[2]); };
  const effBg = (el) => { let img = 0;
    for (let a = el; a; a = a.parentElement) { const c = getComputedStyle(a);
      if (c.backgroundImage && c.backgroundImage !== 'none') img = 1;
      const b = pc(c.backgroundColor); if (b[3] > 0.5) return [b, img]; }
    return [[255,255,255,1], img]; };
  const scaleOf = (t) => { if (!t || t === 'none') return 1; const m = t.match(/matrix\(([^)]+)\)/);
    if (!m) return 1; const v = m[1].split(',').map(parseFloat); return Math.min(Math.hypot(v[0], v[1]), Math.hypot(v[2], v[3])); };
  const idx = new Map(); all.forEach((e, i) => idx.set(e, i));
  const cands = [];
  for (const el of all) {
    if (cands.length >= maxCand) break;
    if (skip.has(el.tagName)) continue;
    const full = (el.textContent || '').replace(/\s+/g, ' ').trim();
    if (!full) continue;
    let own = ''; for (const n of el.childNodes) if (n.nodeType === 3) own += n.nodeValue;
    own = own.replace(/\s+/g, ' ').trim();
    const cs = getComputedStyle(el);
    let op = 1, dispNone = 0, visHid = 0, clip = 0, zeroOv = 0, scale = 1, indent = 0, depth = 0;
    for (let a = el; a && a !== root.parentElement; a = a.parentElement) {
      const c = getComputedStyle(a); depth++;
      op *= parseFloat(c.opacity);
      if (c.display === 'none') dispNone = 1;
      if (c.clip && c.clip !== 'auto' && c.position === 'absolute') clip = 1;
      if (c.clipPath && c.clipPath !== 'none') clip = 1;
      scale *= scaleOf(c.transform);
      if (parseFloat(c.textIndent) <= -500) indent = 1;
      if (a !== el && c.overflow !== 'visible') { const r = a.getBoundingClientRect(); if (r.width <= 1 || r.height <= 1) zeroOv = 1; }
    }
    if (cs.visibility !== 'visible') visHid = 1;
    const r = el.getBoundingClientRect();
    const off = (r.right <= 0 || r.bottom <= 0 || r.left >= docW || r.top >= docH) ? 1 : 0;
    const offDist = Math.max(0, -r.right, -r.bottom, r.left - docW, r.top - docH);
    const fs = parseFloat(cs.fontSize) || 0;
    const col = pc(cs.color); const fill = pc(cs.webkitTextFillColor || cs.color);
    const [bg, bgImg] = effBg(el);
    const l1 = lum(col), l2 = lum(bg); const contrast = (Math.max(l1,l2)+0.05)/(Math.min(l1,l2)+0.05);
    let cv = 1; try { cv = el.checkVisibility({opacityProperty: true, visibilityProperty: true}) ? 1 : 0; } catch (e) {}
    const p = el.parentElement; const parent = (p && p !== root && idx.has(p)) ? idx.get(p) : -1;
    cands.push({i: idx.get(el), parent, tag: el.tagName.toLowerCase(), text: full.slice(0, 600), own: own.slice(0, 600),
      href: (el.getAttribute('href') || '').slice(0, 200),
      f: {op, dispNone, visHid, clip, zeroOv, scale, indent, off, offDist: Math.min(offDist, 100000),
          fs, colA: col[3], fillA: fill[3], contrast, bgImg, cv, w: r.width, h: r.height, depth,
          nchild: el.children.length, ownLen: own.length, fullLen: full.length}});
  }
  const gold = goldSels.map(s => { try { const m = root.querySelectorAll(s); return m.length === 1 ? idx.get(m[0]) : -1; }
                                    catch (e) { return -1; } });
  return {cands, gold, nall: all.length};
}
"""


def page_html(s):
    return f'<!doctype html><html><head><meta charset="utf-8"><style>{s["css"]}</style></head><body><div id="root">{s["html"]}</div></body></html>'


def work(chunk):
    from playwright.sync_api import sync_playwright
    out = []
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        ctx = b.new_context(java_script_enabled=False, viewport={"width": 1280, "height": 800})
        pg = ctx.new_page()
        pg.route("**/*", lambda r: r.abort())
        for s in chunk:
            rec = {"id": s["id"], "cat": s["cat"], "subtype": s["subtype"], "gold": s["gold"]}
            try:
                pg.set_content(page_html(s), wait_until="domcontentloaded", timeout=15000)
                res = pg.evaluate(JS, [MAX_CAND, [g[0] for g in s["gold"]]])
                rec.update(cands=res["cands"], gold_idx=res["gold"], nall=res["nall"], error=None)
            except Exception as e:  # 그리지 못한 표본은 기록만 하고 넘어간다
                rec.update(cands=[], gold_idx=[-1] * len(s["gold"]), nall=0, error=str(e)[:200])
            out.append(rec)
        b.close()
    return out


def main():
    data, outp = sys.argv[1], Path(sys.argv[2])
    nw = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    samples = load_samples(data)
    chunks = [samples[i::nw] for i in range(nw)]
    outp.parent.mkdir(parents=True, exist_ok=True)
    with Pool(nw) as pool:
        res = [r for part in pool.map(work, chunks) for r in part]
    res.sort(key=lambda r: r["id"])
    with open(outp, "w", encoding="utf-8") as f:
        for r in res:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    err = sum(1 for r in res if r["error"])
    print(f"표본 {len(res)}건, 그리기 실패 {err}건, 후보 합계 {sum(len(r['cands']) for r in res)}")


if __name__ == "__main__":
    main()
