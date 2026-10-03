"""저장한 원문 HTML 을 JS 끄고 네트워크 전부 차단한 채 렌더링해서
화면에 실제로 보이는 텍스트 중 도박 어휘가 든 요소를 뽑는다 (해킹 페이지를 안전하게 보는 용도).

사용: python render_offline.py file.html [file2.html ...]
"""
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

KW = r"(카지노|바카라|토토|슬롯|먹튀|놀이터|꽁머니|첫충|가입코드|룰렛|베팅|배팅|홀덤|파워볼)"
JS = r"""
(kw) => {
  const re = new RegExp(kw);
  const out = [];
  for (const el of document.body.querySelectorAll('*')) {
    let own = '';
    for (const n of el.childNodes) if (n.nodeType === 3) own += n.nodeValue;
    own = own.replace(/\s+/g, ' ').trim();
    if (!own || !re.test(own)) continue;
    const r = el.getBoundingClientRect();
    const vis = el.checkVisibility({checkOpacity: true, checkVisibilityCSS: true}) && r.width > 1 && r.height > 1;
    out.push({tag: el.tagName.toLowerCase(), cls: el.className && el.className.baseVal === undefined ? el.className : '',
              visible: vis, text: own.slice(0, 120)});
  }
  return out;
}
"""


def main(files: list[str]) -> None:
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        ctx = b.new_context(java_script_enabled=False, viewport={"width": 1280, "height": 900})
        ctx.route("**/*", lambda r: r.abort())  # 외부 요청 전부 차단
        page = ctx.new_page()
        for f in files:
            html = Path(f).read_bytes().decode("utf-8", "replace")
            page.set_content(html, wait_until="domcontentloaded")
            items = page.evaluate(JS, KW)
            vis = [i for i in items if i["visible"]]
            print(f"== {Path(f).name}: 도박어휘 요소 {len(items)} / 보이는 것 {len(vis)}")
            for i in vis[:8]:
                print("   VIS", json.dumps(i, ensure_ascii=False))
        b.close()


if __name__ == "__main__":
    main(sys.argv[1:])
