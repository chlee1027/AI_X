"""사람 3 OFFSCREEN 점검 결과 고치기 (2026-10-05, 역할 C).

1. 삭제: 상품명이 점(.)으로 가려져 광고 내용이 없는 원문(Ranum 사본 7개)과 그 원문으로 만든 시험용 샘플
2. 수정 (원문)
   - css 칸이 선택자 없는 선언뿐이고 숨김을 건 부모 태그가 발췌에 없어 html+css 만으로 안 숨겨지는 것:
     메타데이터(css_evidence)의 원래 부모 여는 태그로 html 을 다시 감싼다. 원래 선언은 그 태그의 inline style 에 그대로 있다.
     css 칸이 선언뿐이면 비운다(유효한 스타일시트가 아님). 선택자 규칙(.adil{...})이면 그대로 둔다
   - evidence 에 태그 조각이 섞인 것: 실제 글자만 남김
   - 선택자가 조각 안에서 하나로 정해지지 않는 것: 유일 선택자로 바꿈
3. subtype: 계획서 5종(font_left_display / visibility_hidden / clip / text_indent / transform_outside)으로 통일. 세부 유형은 notes 에
4. 덧붙이기(add.yaml, 선택): 새 원문
그리고 원문·시험용 전부를 브라우저로 다시 띄워 숨김·선택자를 검증한다.
사용: python tools/build/fix_offscreen.py 사람3_원본_폴더 out_dir [add.yaml]
(원본은 사람3_최종결과_20261005. 그 결과가 data/offscreen 의 10-05 판이다)
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "validate"))
from check_offscreen import JS  # noqa: E402

REDACTED = {"OF-161", "OF-162", "OF-163", "OF-164", "OF-166", "OF-167", "OF-168"}
MAP = {"font_left_display": "font_left_display", "font_size_zero_or_tiny": "font_left_display", "negative_position": "font_left_display",
       "font_size_0_1px": "font_left_display", "left_negative": "font_left_display", "display_none": "font_left_display",
       "visibility_hidden": "visibility_hidden", "clip": "clip", "clip_clip_path": "clip", "text_indent": "text_indent",
       "negative_text_indent": "text_indent", "transform_outside": "transform_outside", "transform_document_coords": "transform_outside"}
TODAY = "2026-10-05"
# 전체 페이지 기준 위치 선택자(body > :nth-child…)라 발췌 조각 안에서 evidence 요소를 못 가리키는 것: evidence 가 든 요소로 직접
SELECTOR_FIX = {"OF-133": "div.anev > a:nth-of-type(2)", "OF-178": "a"}


def render(pg, x: dict) -> dict:
    pg.set_content(f"<!doctype html><html><head><style>{x.get('css') or ''}</style></head><body>{x['html']}</body></html>")
    return pg.evaluate(JS, x["expected_location"])


def closing(open_tag: str) -> str:
    return "</" + re.match(r"<\s*(\w+)", open_tag).group(1) + ">"


UNIQ = r"""(sel) => { const el = document.querySelector(sel); if (!el) return null;
  const seg = e => { let s = e.tagName.toLowerCase(); if (e.id) return s + '#' + CSS.escape(e.id);
    const c = [...e.classList].slice(0, 2).map(c => '.' + CSS.escape(c)).join(''); return s + c; };
  const chain = []; for (let e = el; e && e !== document.body; e = e.parentElement) chain.unshift(e);
  for (let i = chain.length - 1; i >= 0; i--) { const s = chain.slice(i).map(seg).join(' > ');
    if (document.querySelectorAll(s).length === 1 && document.querySelector(s) === el) return s; }
  return null; }"""


def main(src: str, out: str, add: str | None = None) -> None:
    src, out = Path(src), Path(out)
    orig = yaml.safe_load((src / "data/originals/offscreen_originals.yaml").read_text(encoding="utf-8"))
    fixt = yaml.safe_load((src / "data/samples/offscreen.yaml").read_text(encoding="utf-8"))
    meta = json.loads((src / "data/originals/원문근거_수집메타데이터.json").read_text(encoding="utf-8"))["original_sample_details"]
    fxmeta = {r["id"]: r for r in json.loads((src / "data/review/fixture_rendering_observations.json").read_text(encoding="utf-8"))
              if r.get("viewport") == "desktop"}
    log = Counter()
    redacted_prev = {meta[i]["previous_record"]["id"] for i in REDACTED if i in meta}
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        ctx = b.new_context(java_script_enabled=False, viewport={"width": 1280, "height": 900})
        ctx.route("**/*", lambda r: r.abort())
        pg = ctx.new_page()
        new_orig = []
        for x in orig:
            if x["id"] in REDACTED:
                log["원문 삭제(상품명 가려짐)"] += 1
                continue
            sub0 = x["subtype"]
            x["subtype"] = MAP[sub0]
            if sub0 != x["subtype"]:
                x["notes"] += f" / {TODAY}: subtype 을 계획서 5종으로 통일({sub0} -> {x['subtype']}, 세부 유형 {sub0})"
            ev = x["evidence_text"]
            if re.search(r"</?\w+>|/\w+>", ev):
                clean = re.sub(r"</?\w*>?|/\w+>", "", ev).strip()
                x["evidence_text"] = clean
                x["notes"] += f" / {TODAY}: evidence 에 섞인 태그 조각 제거({ev!r} -> {clean!r})"
                log["evidence 태그 조각 제거"] += 1
            # 보고서 웹페이지에서 코드를 복사할 때 태그 안 공백이 U+00A0 으로 바뀐 것: 태그 안쪽만 일반 공백으로 (글자는 그대로)
            fixed_html = re.sub(r"<[^>]*>", lambda m: m.group(0).replace("\xa0", " "), x["html"])
            if x.get("css") and "\xa0" in x["css"]:
                x["css"] = x["css"].replace("\xa0", " ")
                fixed_html = fixed_html  # css 도 같은 복사 흔적
                log["css 안 U+00A0 정리"] += 1
            if fixed_html != x["html"]:
                x["html"] = fixed_html
                x["notes"] += f" / {TODAY}: 태그 안의 줄바꿈 없는 공백(U+00A0, 보고서 복사 흔적)을 일반 공백으로 바꿔 태그가 읽히게 함"
                log["태그 안 U+00A0 정리"] += 1
            if x["id"] in SELECTOR_FIX:
                x["notes"] += f" / {TODAY}: 선택자가 전체 페이지 기준 위치({x['expected_location']})라 발췌 조각의 evidence 요소({SELECTOR_FIX[x['id']]})로 바꿈"
                x["expected_location"] = SELECTOR_FIX[x["id"]]
                log["선택자 바꿈(페이지 기준 -> 조각 기준)"] += 1
            r = render(pg, x)
            if r.get("count") != 1:
                sel = pg.evaluate(UNIQ, x["expected_location"])
                if sel:
                    x["notes"] += f" / {TODAY}: 선택자가 조각 안에서 하나로 정해지지 않아 바꿈({x['expected_location']} -> {sel})"
                    x["expected_location"] = sel
                    log["선택자 유일하게 수정"] += 1
                    r = render(pg, x)
            if r.get("count") == 1 and not r.get("hidden"):
                pr = meta.get(x["id"], {}).get("previous_record", {})
                ce = pr.get("css_evidence") or []
                tags = [c.get("open_tag_original") for c in ce if isinstance(c, dict) and c.get("open_tag_original")]
                fixed = False
                for tag in tags:
                    cand = dict(x)
                    cand["html"] = tag + x["html"] + closing(tag)
                    if cand.get("css") and "{" not in cand["css"]:
                        cand["css"] = ""
                    rr = render(pg, cand)
                    if rr.get("count") == 1 and rr.get("hidden"):
                        x.update(html=cand["html"], css=cand["css"])
                        x["notes"] += (f" / {TODAY}: html 발췌에 숨김을 건 원래 부모 태그가 빠져 있어, 수집 메타데이터(css_evidence)의 원래 여는 태그로 "
                                       f"감싸 숨김이 재현되게 함. css 칸의 선택자 없는 선언은 그 태그의 inline style 과 같아 비움")
                        log["부모 태그 복원으로 숨김 재현"] += 1
                        fixed = True
                        break
                if not fixed:
                    # 보고서가 숨김 선언만 싣고 감싸던 요소는 안 실은 경우: 원래 선언은 그대로 두고 감싸는 요소를 재구성
                    css0 = (x.get("css") or "").strip()
                    wrap = None
                    js = re.findall(r"style\.(\w+)\s*=\s*'([^']+)'", css0)
                    idm = re.search(r"getElementById\('([^']+)'\)", css0)
                    if js:
                        decl = "; ".join(f"{k}:{v}" for k, v in js)
                        wrap = (f'<div id="{idm.group(1) if idm else "hide"}" style="{decl}">', "")
                    elif "{" in css0:
                        selm = re.match(r"\s*([.#])([\w-]+)", css0)
                        if selm and not re.search(rf'(class|id)\s*=\s*["\']?[^>"\']*\b{re.escape(selm.group(2))}\b', x["html"]):
                            attr = "class" if selm.group(1) == "." else "id"
                            wrap = (f'<div {attr}="{selm.group(2)}">', css0)
                    elif ":" in css0:
                        wrap = (f'<div style="{css0}">', "")
                    if wrap:
                        cand = dict(x)
                        cand["html"] = wrap[0] + x["html"] + "</div>"
                        cand["css"] = wrap[1]
                        rr = render(pg, cand)
                        if rr.get("count") == 1 and rr.get("hidden"):
                            x.update(html=cand["html"], css=cand["css"])
                            x["notes"] += (f" / {TODAY}: 공개 보고서가 숨김 선언({css0[:60]})만 싣고 그 선언이 걸린 감싸는 요소는 싣지 않아, "
                                           f"원래 선언을 그대로 쓴 감싸는 요소를 재구성해 숨김이 재현되게 함(감싸는 태그 자체는 원문이 아님)")
                            log["감싸는 요소 재구성으로 숨김 재현"] += 1
                            fixed = True
                if not fixed:
                    log["숨김 재현 못 함"] += 1
                    x["notes"] += f" / {TODAY}: 발췌 html·css 만으로는 숨김이 재현되지 않음(근거 기록용)"
                    x["_unreproduced"] = True
            new_orig.append(x)
        if add:
            for x in yaml.safe_load(Path(add).read_text(encoding="utf-8")) or []:
                new_orig.append(x)
                log["원문 추가"] += 1
        # 시험용: 삭제된 원문에서 만든 것 제외, subtype 통일
        new_fixt = []
        for x in fixt:
            det = str(fxmeta.get(x["id"], {}).get("sample_details", ""))
            m = re.search(r"'original_id': '([^']+)'", det)
            if m and m.group(1) in redacted_prev:
                log["시험용 삭제(가려진 원문에서 만든 것)"] += 1
                continue
            sub0 = x["subtype"]
            x["subtype"] = MAP[sub0]
            if sub0 != x["subtype"]:
                x["notes"] += f" / {TODAY}: subtype 을 계획서 5종으로 통일({sub0} -> {x['subtype']})"
            ev = x["evidence_text"]
            if re.search(r"</?\w+>|/\w+>", ev):
                x["evidence_text"] = re.sub(r"</?\w*>?|/\w+>", "", ev).strip()
                x["notes"] += f" / {TODAY}: evidence 에 섞인 태그 조각 제거"
                log["시험용 evidence 태그 조각 제거"] += 1
            new_fixt.append(x)
        # 최종 검증
        bad = []
        for name, xs in (("원문", new_orig), ("시험용", new_fixt)):
            for x in xs:
                r = render(pg, x)
                h = x["html"]
                if r.get("count") != 1 or (x["is_positive"] and not r.get("hidden") and not x.get("_unreproduced")) or \
                        x["evidence_text"] not in re.sub(r"<[^>]+>", "", h).replace("&amp;", "&"):
                    bad.append((name, x["id"], r.get("count"), r.get("hidden"), x["evidence_text"][:20]))
        b.close()
    for x in new_orig:
        x.pop("_unreproduced", None)
    (out / "data/originals").mkdir(parents=True, exist_ok=True)
    (out / "data/samples").mkdir(parents=True, exist_ok=True)
    (out / "data/originals/offscreen_originals.yaml").write_text(yaml.safe_dump(new_orig, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
    (out / "data/samples/offscreen.yaml").write_text(yaml.safe_dump(new_fixt, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
    print(dict(log))
    print("원문", len(new_orig), Counter(x["subtype"] for x in new_orig))
    print("시험용", len(new_fixt), Counter(x["subtype"] for x in new_fixt))
    print("검증 문제", bad[:15])


if __name__ == "__main__":
    main(*sys.argv[1:4])
