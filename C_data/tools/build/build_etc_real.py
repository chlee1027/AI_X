"""ETC 실사례 -> 샘플. 저장한 해킹 페이지 원문을 JS 끄고 네트워크 막은 채 띄워서
대상 링크와 조상 3단을 잘라 내고, 조각 안에서 유일한 선택자를 만든다.

사용: python build_etc_real.py out.yaml
"""
import json
import sys
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

RAW = Path(__file__).resolve().parents[2] / "data" / "raw" / "etc"

# (원문 파일, 대상 href, 앵커 텍스트, 수집 메모)
CASES = [
    ("r1/f8f7840c81_browser.html", "https://wwnnh.com/gate/kr/kr072750.html", "로그인",
     "Referer=google 요청 시 같은 호스트가 wwnnh.com/gate 로 302 리다이렉트(fetch_log 확인). 목적지 미방문"),
    ("r1/a3e3408108_browser.html", "http://bit.ly/heimao_krclub", "로그인",
     "Referer=google 요청 시 tracker.uuassdf22ssfsdddonline.top 으로 302. 단축 URL 목적지 미방문·미확인"),
    ("r2/da5d15aaa8_browser.html", "https://bit.ly/heimao_krclub", "회원가입",
     "Referer=google 요청 시 wwnnh.com/gate 로 302. 단축 URL 목적지 미방문·미확인"),
    ("r1/ba9833305c_browser.html", "https://adhub.pages.dev/", "로그인",
     "Referer=google 요청 시 tracker.uuassdf22ssfsdddonline.top 으로 301. 목적지 미방문·미확인"),
]

CUT = r"""
([href, text]) => {
  const a = [...document.querySelectorAll('a')].find(e => e.getAttribute('href') === href && e.textContent.trim() === text);
  if (!a) return null;
  let node = a.cloneNode(true), cur = a;
  for (let i = 0; i < 3 && cur.parentElement && cur.parentElement !== document.body; i++) {
    cur = cur.parentElement; const sh = cur.cloneNode(false); sh.appendChild(node); node = sh;
  }
  node.querySelectorAll('script,style,img,svg').forEach(n => n.remove());
  return node.outerHTML;
}
"""
LOC = r"""
([href]) => {
  const el = [...document.querySelectorAll('a')].find(e => e.getAttribute('href') === href);
  const seg = e => e.tagName.toLowerCase() + [...e.classList].slice(0, 3).map(c => '.' + CSS.escape(c)).join('');
  const parts = [];
  for (let e = el; e && e !== document.body; e = e.parentElement) {
    parts.unshift(seg(e)); const s = parts.join(' > ');
    const m = document.querySelectorAll(s); if (m.length === 1 && m[0] === el) return s;
  }
  return null;
}
"""


def main(out: str) -> None:
    items = []
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        ctx = b.new_context(java_script_enabled=False)
        ctx.route("**/*", lambda r: r.abort())
        pg = ctx.new_page()
        for k, (f, href, text, memo) in enumerate(CASES, 1):
            meta = json.loads((RAW / f).with_suffix(".json").read_text(encoding="utf-8"))
            pg.set_content((RAW / f).read_bytes().decode("utf-8", "replace"), wait_until="domcontentloaded")
            snip = pg.evaluate(CUT, [href, text])
            pg.set_content(f"<!doctype html><html><body>{snip}</body></html>")
            loc = pg.evaluate(LOC, [href])
            items.append({
                "id": f"ET-{k:03d}", "category": "ETC", "subtype": "link_cloaking", "html": snip, "css": "",
                "evidence_text": href, "expected_location": loc, "is_positive": True,
                "extra_finding": "LINK_CLOAKING",
                "source": f"실측: 해킹된 대학 도메인의 도어웨이 페이지 {meta['url']} (2026-10-03 수집)",
                "notes": f"앵커 텍스트 '{text}' 는 정상 문구, href 는 도박 게이트. {memo}. 원문 data/raw/etc/{f}",
            })
        b.close()
    Path(out).write_text(yaml.safe_dump(items, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
    for i in items:
        print(i["id"], i["expected_location"], "|", i["html"][:160])


if __name__ == "__main__":
    main(sys.argv[1])
