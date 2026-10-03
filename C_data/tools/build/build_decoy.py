"""덤프(JSON) -> DECOY 후보 샘플(YAML).

a11y_sr_only : 화면에서는 숨겼지만 보조기기에는 읽히는 것 (clip·1px·오프셋·text-indent·font-size). display:none 제외
hidden_menu  : display:none·visibility:hidden 로 닫혀 있는 메뉴·모달·탭 항목
policy_text / risky_word_normal : 보이는 본문 중 위험 어휘가 든 문단 (kind=risky_visible)

다양성: (사이트, 숨김 요소 클래스) 한 쌍에서 하나만. 도박 광고 어휘가 든 것은 DECOY 에서 뺀다.
재현: 잘라낸 html + 규칙 원문만 띄워서 숨김(또는 보임)이 재현되고, 선택자가 조각 안에서 유일한 것만 남긴다.

사용: python build_decoy.py out_candidates.yaml dump_dir [dump_dir ...]
"""
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from playwright.sync_api import sync_playwright

AD = re.compile(r"카지노|바카라|토토|슬롯|먹튀|놀이터|꽁머니|첫충|베팅|배팅|홀덤|파워볼")
POLICY = re.compile(r"(불법|사행|도박).{0,40}(신고|근절|예방|단속|주의|중독|치유|상담|금지|처벌|피해)|"
                    r"(신고|예방|단속|중독|치유).{0,40}(불법|사행|도박)")
RISKY_NORMAL = ["환전", "상담", "보너스", "지급", "무료 체험", "무료체험", "바로가기", "포인트", "적립", "이벤트", "당첨", "경품"]

# 조각 안에서 대상 요소를 다시 찾고 유일 선택자를 만든다 (probe_hidden.js 와 같은 규칙)
LOCATE = r"""
([tag, text]) => {
  const norm = s => s.replace(/\s+/g, ' ').trim();
  const own = el => { let s = ''; for (const n of el.childNodes) if (n.nodeType === 3) s += n.nodeValue; return s; };
  const cands = [...document.body.querySelectorAll(tag)].filter(el => norm(own(el)) === text);
  if (cands.length !== 1) return { err: 'target_' + cands.length };
  const el = cands[0];
  const isDyn = c => /^(css|sc|jsx|svelte|emotion)-|[0-9a-f]{6,}/.test(c) || c.length > 40;
  const seg = e => { let s = e.tagName.toLowerCase();
    const cls = [...e.classList].filter(c => !isDyn(c)).slice(0, 3);
    if (e.id && !/\d{3,}/.test(e.id)) return s + '#' + CSS.escape(e.id);
    return s + cls.map(c => '.' + CSS.escape(c)).join(''); };
  const nth = e => { let i = 1; for (let p = e.previousElementSibling; p; p = p.previousElementSibling) if (p.tagName === e.tagName) i++; return `:nth-of-type(${i})`; };
  const chain = []; for (let e = el; e && e !== document.body; e = e.parentElement) chain.push(e);
  let sel = null;
  for (const useNth of [false, true]) {
    const parts = [];
    for (const e of chain) {
      parts.unshift(seg(e) + (useNth ? nth(e) : ''));
      const s = parts.join(' > ');
      const m = document.querySelectorAll(s);
      if (m.length === 1 && m[0] === el) { sel = s; break; }
    }
    if (sel) break;
  }
  if (!sel) return { err: 'no_unique' };
  // 원문 텍스트: 공백 정리 전 텍스트 노드 그대로 (앞뒤 공백만 뺀다)
  let raw = ''; for (const n of el.childNodes) if (n.nodeType === 3 && n.nodeValue.trim()) { raw = n.nodeValue.trim(); break; }
  // 보이는 면적
  let area = 0;
  if (el.checkVisibility({ checkOpacity: true, checkVisibilityCSS: true }) && parseFloat(getComputedStyle(el).fontSize) > 1) {
    const r = el.getBoundingClientRect(); let x1 = r.left, y1 = r.top, x2 = r.right, y2 = r.bottom;
    for (let e = el; e && e.nodeType === 1; e = e.parentElement) {
      const cs = getComputedStyle(e), er = e.getBoundingClientRect();
      if (/rect\(/.test(cs.clip) && cs.position !== 'static') { const n = cs.clip.match(/-?[\d.]+/g).map(Number);
        x1 = Math.max(x1, er.left + n[3]); x2 = Math.min(x2, er.left + n[1]); y1 = Math.max(y1, er.top + n[0]); y2 = Math.min(y2, er.top + n[2]); }
      if (/inset\(\s*(50|100)%/.test(cs.clipPath)) { x2 = x1; }
      if (e !== el && cs.overflow !== 'visible') { x1 = Math.max(x1, er.left); x2 = Math.min(x2, er.right); y1 = Math.max(y1, er.top); y2 = Math.min(y2, er.bottom); }
    }
    x1 = Math.max(x1, 0); y1 = Math.max(y1, 0);
    const w = Math.max(0, x2 - x1), h = Math.max(0, y2 - y1); area = (w <= 1 || h <= 1) ? 0 : w * h;
  }
  return { sel, raw, area };
}
"""


def classify(it: dict) -> str | None:
    if AD.search(it["text"]):
        return None
    if it["kind"] == "hidden":
        rs = " ".join(it["hide_reasons"])
        if "display:none" in rs or "visibility:hidden" in rs:
            return "hidden_menu" if (it["in_nav"] or it["in_modal"] or it["tag"] in ("a", "li", "span", "button")) else None
        if re.search(r"clip|size:|offset|text-indent|font-size", rs):
            return "a11y_sr_only"
        return None
    if POLICY.search(it["text"]) and len(it["text"]) >= 30:
        return "policy_text"
    if any(w in it["text"] for w in RISKY_NORMAL) and len(it["text"]) >= 15:
        return "risky_word_normal"
    return None


STRONG = re.compile(r"(?:^|[;{\s])(display|visibility|clip|clip-path|position|left|top|width|height|overflow|opacity|"
                    r"text-indent|font-size|transform)\s*:")


def hiding_rules(rules: list[dict]) -> list[str]:
    """리셋 규칙(* · html, body, div ...)과 margin/padding 만 있는 규칙은 숨김 원인이 아니므로 뺀다."""
    out = []
    for r in rules:
        t = r.get("text")
        if not t:
            continue
        sel = t.split("{", 1)[0].strip()
        if sel == "*" or sel.startswith("html, body") or sel.count(",") > 8:
            continue
        if STRONG.search("{" + t.split("{", 1)[1]):
            out.append(t)
    return out


def class_key(it: dict) -> str:
    return re.sub(r":nth-of-type\(\d+\)", "", it.get("hide_tag") or it["tag"])


def main(out: str, dirs: list[str]) -> None:
    pool: dict[str, list] = {"a11y_sr_only": [], "hidden_menu": [], "policy_text": [], "risky_word_normal": []}
    seen = set()
    for d in dirs:
        for f in sorted(Path(d).glob("*.json")):
            page = json.loads(f.read_text(encoding="utf-8"))
            host = urlsplit(page["url"]).netloc
            for it in page["items"]:
                sub = classify(it)
                if not sub:
                    continue
                key = (host, sub, class_key(it)) if sub in ("a11y_sr_only", "hidden_menu") else (host, sub, it["text"][:40])
                if key in seen:
                    continue
                seen.add(key)
                pool[sub].append((page, it))
    print({k: len(v) for k, v in pool.items()})

    out_items = []
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        pg = b.new_page(viewport={"width": 1280, "height": 900})
        pg.route("**/*", lambda r: r.abort() if r.request.url.startswith("http") else r.continue_())
        for sub, cands in pool.items():
            for page, it in cands:
                css = "\n".join(hiding_rules(it["rules"]))
                html = re.sub(r"\s+\n", "\n", it["snippet_html"])
                pg.set_content(f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style></head>"
                               f"<body>{html}</body></html>")
                r = pg.evaluate(LOCATE, [it["tag"], it["text"]])
                if "err" in r:
                    continue
                hidden_ok = r["area"] == 0
                if sub in ("a11y_sr_only", "hidden_menu") and not hidden_ok:
                    continue
                if sub in ("policy_text", "risky_word_normal") and hidden_ok:
                    continue
                out_items.append({
                    "subtype": sub, "html": html, "css": css, "evidence_text": r["raw"],
                    "expected_location": r["sel"], "source": f"{page['title'].strip()[:60]} | {page['url']}",
                    "_hide_reasons": it["hide_reasons"], "_fetched_at": page["fetched_at"],
                    "_rule_sheets": sorted({x["sheet"] for x in it["rules"] if x.get("text")}),
                })
        b.close()
    Path(out).write_text(yaml.safe_dump(out_items, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
    from collections import Counter
    print("재현 통과:", Counter(i["subtype"] for i in out_items))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
