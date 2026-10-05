"""OFFSCREEN 샘플 독립 검증 (2026-10-05, 역할 C).

각 샘플의 html + css 만 띄워(JS 끔, 네트워크 막음) expected_location 이
  - 조각 안에서 정확히 하나만 맞는지
  - 사람 눈에 실제로 안 보이는지 (아래 중 하나)
    display:none / visibility:hidden 계통, font-size<=1px, 화면(문서) 밖 좌표, clip·clip-path 로 잘림,
    text-indent 로 글자가 상자 밖, 크기 0 + overflow:hidden, opacity 0
를 브라우저 계산 스타일과 위치로 판정한다. 어떤 이유로 숨겨졌는지도 남긴다.
evidence 에 태그 조각이 섞였는지, 광고 문구가 가려져(...) 내용이 안 보이는지도 센다.
사용: python tools/validate/check_offscreen.py data/offscreen/data/samples/offscreen.yaml out.json
(원문은 data/offscreen/data/originals/offscreen_originals.yaml, 대조군은 data/offscreen/data/samples/offscreen_controls.json)
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

JS = r"""
(sel) => {
  const els = document.querySelectorAll(sel);
  if (els.length !== 1) return {count: els.length};
  const el = els[0];
  const why = [];
  for (let e = el; e && e !== document.documentElement; e = e.parentElement) {
    const s = getComputedStyle(e);
    if (s.display === 'none') { why.push('display:none' + (e === el ? '' : '(조상)')); break; }
  }
  const s = getComputedStyle(el);
  if (s.visibility === 'hidden' || s.visibility === 'collapse') why.push('visibility:' + s.visibility);
  if (parseFloat(s.fontSize) <= 1) why.push('font-size:' + s.fontSize);
  let op = 1; for (let e = el; e && e !== document.documentElement; e = e.parentElement) op *= parseFloat(getComputedStyle(e).opacity);
  if (op === 0) why.push('opacity:0');
  const r = el.getBoundingClientRect();
  const W = document.documentElement.scrollWidth, H = document.documentElement.scrollHeight;
  if (r.right <= 0 || r.bottom <= 0 || r.left >= Math.max(W, innerWidth) + 1000 || r.top >= Math.max(H, innerHeight) + 1000) why.push('문서 밖 좌표');
  for (let e = el; e && e !== document.documentElement; e = e.parentElement) {
    const t = getComputedStyle(e);
    const cr = e.getBoundingClientRect();
    const cm = t.clip && t.clip.match(/rect\(([^)]*)\)/);
    if (cm && t.position !== 'static') {
      // clip:rect(위, 오른쪽, 아래, 왼쪽). auto 는 상자 끝. 보이는 영역이 비면 숨김
      const v = cm[1].split(/[, ]+/).filter(Boolean).map(q => q === 'auto' ? null : parseFloat(q));
      const top = v[0] ?? 0, right = v[1] ?? cr.width, bottom = v[2] ?? cr.height, left = v[3] ?? 0;
      if (Math.min(right, cr.width) - Math.max(left, 0) <= 1 || Math.min(bottom, cr.height) - Math.max(top, 0) <= 1) { why.push('clip'); break; }
    }
    if (
        (t.clipPath && t.clipPath !== 'none' && /inset\(\s*(50%|100%)|circle\(\s*0|polygon\(\s*0(px)?\s+0(px)?\s*\)/.test(t.clipPath))) { why.push('clip'); break; }
    const rr = e.getBoundingClientRect();
    if ((rr.width <= 1 || rr.height <= 1) && (t.overflow === 'hidden' || t.overflowX === 'hidden' || t.overflowY === 'hidden')) { why.push('크기0+overflow'); break; }
  }
  const ti = parseFloat(s.textIndent);
  if (Math.abs(ti) >= 999 || (ti < 0 && r.right + ti <= 0)) why.push('text-indent:' + s.textIndent);
  if (/translate|matrix/.test(s.transform) && (r.right <= 0 || r.bottom <= 0)) why.push('transform 밖');
  return {count: 1, hidden: why.length > 0, why, rect: [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)]};
}
"""


def main(src: str, out: str) -> None:
    xs = yaml.safe_load(Path(src).read_text(encoding="utf-8"))
    res = []
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        ctx = b.new_context(java_script_enabled=False, viewport={"width": 1280, "height": 900})
        ctx.route("**/*", lambda r: r.abort())
        pg = ctx.new_page()
        for x in xs:
            pg.set_content(f"<!doctype html><html><head><style>{x.get('css') or ''}</style></head><body>{x['html']}</body></html>")
            try:
                r = pg.evaluate(JS, x["expected_location"])
            except Exception as e:  # noqa: BLE001
                r = {"count": -1, "error": str(e)[:80]}
            ev = x["evidence_text"]
            r.update({"id": x["id"], "subtype": x["subtype"], "is_positive": x["is_positive"],
                      "tag_in_evidence": bool(re.search(r"</?\w+>|/\w+>", ev)),
                      "redacted": bool(re.fullmatch(r"[\s.·*]*\w{0,12}[\s.·*]+", ev)) or ev.count(".") >= 3 and len(re.sub(r"[\s.]", "", ev)) < 10})
            res.append(r)
        b.close()
    Path(out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    pos = [r for r in res if r["is_positive"]]
    print("샘플", len(res), "| 선택자 유일 아님", [r["id"] for r in res if r["count"] != 1][:10])
    print("positive 인데 보이는 것", [(r["id"], r["subtype"], r.get("rect")) for r in pos if r["count"] == 1 and not r["hidden"]][:15])
    print("숨김 이유", Counter(w.split(":")[0].split("(")[0] for r in pos if r.get("hidden") for w in r["why"][:1]))
    print("evidence 에 태그 조각", [r["id"] for r in res if r["tag_in_evidence"]], "| 가려진 문구", [r["id"] for r in res if r["redacted"]])


if __name__ == "__main__":
    main(*sys.argv[1:3])
