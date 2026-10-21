"""v4 검사용 특징 추출 JS (10-17). model/render.py(동결)의 JS 에 숨김 특징 넷만 더한다. render.py 자체는 바꾸지 않는다.

check_css.py(숨김 CSS 방법 목록 점검)에서 v2 규칙이 못 잡은 방법을 잡기 위한 것:
  selfOv : 요소 자신이 overflow 를 숨기고 너비나 높이가 1px 이하(자기 1px 상자·높이 0·max-height 0).
           render.py 의 zeroOv 는 조상 상자만 본다(a !== el).
  cvh    : 자신이나 조상의 content-visibility:hidden
  zm     : 자신과 조상의 zoom 누적(글꼴 크기 x zm 이 1px 이하면 화면 밖 은닉으로 본다)
  fop    : 자신과 조상의 filter:opacity() 누적
개발 데이터 캐시(features.jsonl)에는 이 특징이 없어 개발 데이터에서는 새 규칙이 켜지지 않는다(.get 기본값).
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "model")]
from render import JS as RENDER_JS  # noqa: E402
from site_scan import PAGE_JS  # noqa: E402

A1 = "const p = el.parentElement; const parent"
A2 = "nchild: el.children.length,"
EXTRA = r"""let fop = 1, zm = 1, cvh = 0;
    for (let a = el; a && a !== root.parentElement; a = a.parentElement) { const c = getComputedStyle(a);
      const m = (c.filter || '').match(/opacity\(([\d.]+)(%?)\)/); if (m) fop *= parseFloat(m[1]) / (m[2] ? 100 : 1);
      zm *= parseFloat(c.zoom) || 1; if (c.contentVisibility === 'hidden') cvh = 1; }
    const selfOv = (cs.overflow !== 'visible' && (r.width <= 1 || r.height <= 1)) ? 1 : 0;
    """
assert RENDER_JS.count(A1) == 1 and RENDER_JS.count(A2) == 1
JS4 = RENDER_JS.replace(A1, EXTRA + A1).replace(A2, A2 + " fop, zm, cvh, selfOv,")
_old = RENDER_JS.replace("document.getElementById('root')", "document.body")
assert PAGE_JS.count(_old) == 1
PAGE_JS4 = PAGE_JS.replace(_old, JS4.replace("document.getElementById('root')", "document.body"))

# 10-19(7-36절): 조상 요소의 글자에 안쪽 <script>·<style> 소스가 섞여 들어가던 것을 뺀다. 스크립트가 늦게 광고를 끼워 넣는 쪽에서
# 스크립트를 품은 묶음 요소가 그 소스 글자(광고 문구 포함) 때문에 광고로 보고되고, 정작 끼워 넣어진 요소는 빠지던 문제.
# 스크립트·스타일을 품은 요소만 바뀐다(나머지는 글자가 그대로). 개발 데이터 캐시는 다시 뽑지 않는다.
T1 = r"const full = (el.textContent || '').replace(/\s+/g, ' ').trim();"
T2 = ("const full = (el.querySelector('script,style,noscript,template') ? (() => { const c = el.cloneNode(true); "
      "c.querySelectorAll('script,style,noscript,template').forEach(x => x.remove()); return c.textContent || ''; })() "
      r": (el.textContent || '')).replace(/\s+/g, ' ').trim();")
assert PAGE_JS4.count(T1) == 1
PAGE_JS4 = PAGE_JS4.replace(T1, T2)
