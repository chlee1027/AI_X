"""DECOY·ETC 샘플 양식 검증 + 렌더링 확인.

검사
1. 양식: 필수 칸, id 형식·중복, category/is_positive/extra_finding/subtype 짝
2. 쿼터: 하위 유형별 개수 (데이터수집 계획 2쪽)
3. 렌더링 (Edge headless): css + html 을 실제로 띄워
   - expected_location 이 정확히 1개 요소에 매칭되는가
   - evidence_text 가 그 요소(텍스트·속성·::before/::after content·원문 html) 안에 있는가
   - 하위 유형이 요구하는 상태인가
     a11y_sr_only·hidden_menu : 화면에 안 보인다 (보이는 면적 0)
     policy_text·risky_word_normal : 화면에 보인다
     zero_width : evidence 에 제로폭 문자가 있다
     link_cloaking : 대상이 a[href] 이고 href 가 evidence 의 광고와 이어진다 (외부 호스트)
     css_content : ::before/::after content 가 비어 있지 않다
     meta_cloaking : 대상이 head 안에 있다
     encoding : html 원문에 숫자 엔티티 또는 base64 덩어리가 있다

사용: python validate_samples.py data/samples/decoy.yaml data/samples/etc.yaml
"""
import re
import sys
from collections import Counter
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

FIELDS = ["id", "category", "subtype", "html", "css", "evidence_text", "expected_location", "is_positive",
          "extra_finding", "source", "notes"]
QUOTA = {
    "DECOY": {"a11y_sr_only": 80, "hidden_menu": 60, "policy_text": 30, "risky_word_normal": 30, "homoglyph_like_normal": 40},  # 2026-10-04 200개로 두 배, 10-08 사람2 검수분
    "ETC": {"zero_width": 30, "link_cloaking": 30, "css_content": 20, "meta_cloaking": 10, "encoding": 10},
}
EXTRA = {"zero_width": "ZERO_WIDTH", "link_cloaking": "LINK_CLOAKING", "css_content": "CSS_CONTENT",
         "meta_cloaking": "META_CLOAKING", "encoding": "ENCODING"}
# 보이지 않는 문자: 제로폭·방향 제어·소프트하이픈·한글 채움 문자 (분석기와 같은 범위)
ZW = re.compile("[​-‏⁠-⁤﻿᠎­͏ᅟᅠㅤﾠ]")
ENC = re.compile(r"&#(?:x[0-9a-fA-F]{2,6}|\d{2,7});|(?:atob\(|base64,)\s*[\"']?[A-Za-z0-9+/=]{12,}|(?:%[0-9A-Fa-f]{2}){3,}")

PROBE = r"""
([loc, evidence]) => {
  const m = document.querySelectorAll(loc);
  if (m.length !== 1) return { count: m.length };
  const el = m[0];
  // 보이는 면적: 자신의 사각형을 overflow 가 잘리는 조상·clip 과 교차
  const visibleArea = (el) => {
    if (!el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true })) return 0;
    const cs0 = getComputedStyle(el);
    if (parseFloat(cs0.fontSize) <= 1 && el.textContent.trim()) return 0;
    let r = el.getBoundingClientRect();
    let x1 = r.left, y1 = r.top, x2 = r.right, y2 = r.bottom;
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
      const cs = getComputedStyle(e);
      const er = e.getBoundingClientRect();
      if (/rect\(/.test(cs.clip) && cs.position !== 'static') {
        const n = cs.clip.match(/-?[\d.]+/g).map(Number); // top right bottom left
        x1 = Math.max(x1, er.left + n[3]); x2 = Math.min(x2, er.left + n[1]);
        y1 = Math.max(y1, er.top + n[0]); y2 = Math.min(y2, er.top + n[2]);
      }
      if (/inset\(\s*(50|100)%/.test(cs.clipPath)) return 0;
      if (e !== el && cs.overflow !== 'visible') {
        x1 = Math.max(x1, er.left); x2 = Math.min(x2, er.right);
        y1 = Math.max(y1, er.top); y2 = Math.min(y2, er.bottom);
      }
    }
    // 문서 밖 (스크롤로도 못 가는 음수 좌표)
    x1 = Math.max(x1, -window.scrollX); y1 = Math.max(y1, -window.scrollY);
    const w = Math.max(0, x2 - x1), h = Math.max(0, y2 - y1);
    return (w <= 1 || h <= 1) ? 0 : w * h;
  };
  const pb = getComputedStyle(el, '::before').content, pa = getComputedStyle(el, '::after').content;
  const attrs = [...el.attributes].map(a => a.value).join(' ');
  return {
    count: 1,
    tag: el.tagName.toLowerCase(),
    in_head: !!el.closest('head'),
    href: el.closest('a') ? el.closest('a').getAttribute('href') : null,
    text: el.textContent,
    attrs,
    pseudo: [pb, pa].filter(c => c && c !== 'none' && c !== 'normal').join(' '),
    area: visibleArea(el),
  };
}
"""


def build_doc(s: dict) -> str:
    css = s.get("css") or ""
    if s["subtype"] == "meta_cloaking":
        return f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style>{s['html']}</head><body><p>본문</p></body></html>"
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head><body>{s['html']}</body></html>"


def check(samples: list[dict], page) -> tuple[list[str], Counter]:
    errs, cnt, ids = [], Counter(), Counter(s.get("id") for s in samples)
    for s in samples:
        sid = s.get("id", "?")
        miss = [f for f in FIELDS if f not in s]
        if miss:
            errs.append(f"{sid}: 칸 없음 {miss}")
            continue
        if ids[sid] > 1:
            errs.append(f"{sid}: id 중복")
        cat, sub = s["category"], s["subtype"]
        if not re.fullmatch(r"(DC|ET)-\d{3}", sid) or (cat == "DECOY") != sid.startswith("DC"):
            errs.append(f"{sid}: id 형식")
        if sub not in QUOTA.get(cat, {}):
            errs.append(f"{sid}: subtype {sub} 이 {cat} 에 없음")
            continue
        cnt[(cat, sub)] += 1
        if cat == "DECOY" and (s["is_positive"] is not False or s["extra_finding"] is not None):
            errs.append(f"{sid}: DECOY 는 is_positive false, extra_finding null")
        if cat == "ETC" and (s["is_positive"] is not True or s["extra_finding"] != EXTRA[sub]):
            errs.append(f"{sid}: ETC 는 is_positive true, extra_finding {EXTRA[sub]}")
        if not str(s["evidence_text"]).strip():
            errs.append(f"{sid}: evidence_text 비어 있음")
        # 렌더링
        page.set_content(build_doc(s), wait_until="load")
        try:
            r = page.evaluate(PROBE, [s["expected_location"], s["evidence_text"]])
        except Exception as e:  # noqa: BLE001
            errs.append(f"{sid}: 선택자 오류 {e.__class__.__name__}")
            continue
        if r["count"] != 1:
            errs.append(f"{sid}: expected_location 매칭 {r['count']}개")
            continue
        ev = str(s["evidence_text"])
        hay = r["text"] + " " + r["attrs"] + " " + r["pseudo"] + " " + s["html"] + " " + (s["css"] or "")
        if ev not in hay:
            errs.append(f"{sid}: evidence_text 가 대상 요소에서 안 나옴")
        if sub in ("a11y_sr_only", "hidden_menu") and r["area"] > 0:
            errs.append(f"{sid}: 숨김이어야 하는데 보임 (면적 {r['area']:.0f})")
        if sub in ("policy_text", "risky_word_normal") and r["area"] == 0:
            errs.append(f"{sid}: 보여야 하는데 안 보임")
        if sub == "zero_width" and not ZW.search(ev):
            errs.append(f"{sid}: evidence 에 제로폭 문자 없음")
        if sub == "link_cloaking" and not (r["href"] and re.match(r"https?://", r["href"])):
            errs.append(f"{sid}: 대상이 외부 a[href] 가 아님")
        if sub == "css_content" and not r["pseudo"]:
            errs.append(f"{sid}: ::before/::after content 없음")
        if sub == "meta_cloaking" and not r["in_head"]:
            errs.append(f"{sid}: 대상이 head 밖")
        if sub == "encoding" and not ENC.search(s["html"]):
            errs.append(f"{sid}: html 에 엔티티/base64 없음")
    return errs, cnt


def main(paths: list[str]) -> int:
    samples = []
    for p in paths:
        data = yaml.safe_load(Path(p).read_text(encoding="utf-8")) or []
        samples += data
    with sync_playwright() as pw:
        b = pw.chromium.launch(channel="msedge")
        page = b.new_page(viewport={"width": 1280, "height": 900})
        errs, cnt = check(samples, page)
        b.close()
    print(f"샘플 {len(samples)}개")
    for cat, q in QUOTA.items():
        for sub, n in q.items():
            got = cnt[(cat, sub)]
            print(f"  {cat:5} {sub:18} {got:3}/{n}{'' if got >= n else '  <- 미달'}")
    print(f"오류 {len(errs)}건")
    for e in errs:
        print("  " + e)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
