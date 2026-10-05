"""OFFSCREEN 묶음의 요약 파일을 지금 데이터에 맞춰 다시 쓰기 (2026-10-06, 역할 C).

사람 3 의 scripts/verify_final_person3_bundle.py 는 시험용 YAML 을 다시 쓰고 검수 CSV 기준으로 다시 계산하므로 쓰지 않는다.
이 도구는 데이터 파일(원문·시험용·대조군·fixtures)은 건드리지 않고 아래만 다시 쓴다.
- 검증결과.json: 원문 100·시험용 100·대조군 7 을 데스크톱(1280x900)·모바일(390x844) 두 화면 크기로 다시 렌더링한 결과
- 최종현황.json: 분류별·출처별·근거 종류별 개수를 지금 원문으로 다시 셈
- data/originals/원문근거_수집메타데이터.json: 보충 원문(메타데이터에 없는 id)의 출처 기록을 넣고, 지금 원문에 없는 id 에 삭제 표시
- 패키지_SHA256.json: 지금 파일로 다시 계산. 묶음에 없는 data/raw/(사람 3 로컬 원본, gitignore) 항목은 그대로 두고, 지운 파일은 뺀다
사람 3 판의 값은 바뀐 항목마다 *_first_edition 키나 role_c_revision 에 남긴다.
사용: python tools/build/refresh_offscreen_meta.py data/offscreen "새 원문 출처 이름"
"""
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import yaml
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "validate"))
from check_offscreen import JS  # noqa: E402

TODAY = "2026-10-06"
VIEWPORTS = {"desktop": {"width": 1280, "height": 900}, "mobile": {"width": 390, "height": 844}}
SUBTYPES = ["font_left_display", "visibility_hidden", "clip", "text_indent", "transform_outside"]


def dump(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def render_all(groups: dict) -> dict:
    out = {}
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        for vp, size in VIEWPORTS.items():
            ctx = b.new_context(java_script_enabled=False, viewport=size)
            reqs = []
            ctx.route("**/*", lambda r: (reqs.append(r.request.url), r.abort()))
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:80]))
            for name, xs in groups.items():
                for x in xs:
                    pg.set_content(f"<!doctype html><html><head><style>{x.get('css') or ''}</style></head><body>{x['html']}</body></html>")
                    r = pg.evaluate(JS, x["expected_location"])
                    txt = pg.evaluate("s => { const e = document.querySelector(s); return e ? e.textContent : null; }", x["expected_location"])
                    r["text_ok"] = txt is not None and re.sub(r"\s+", " ", x["evidence_text"]).strip() in re.sub(r"\s+", " ", txt)
                    out[(name, vp, x["id"])] = r
            out[("_net", vp)] = len(reqs)
            out[("_err", vp)] = errs
            ctx.close()
        b.close()
    return out


def main(bundle: str, new_publisher: str) -> None:
    B = Path(bundle)
    orig = yaml.safe_load((B / "data/originals/offscreen_originals.yaml").read_text(encoding="utf-8"))
    fixt = yaml.safe_load((B / "data/samples/offscreen.yaml").read_text(encoding="utf-8"))
    ctrl = json.loads((B / "data/samples/offscreen_controls.json").read_text(encoding="utf-8"))

    # 1. 원문 메타데이터
    mpath = B / "data/originals/원문근거_수집메타데이터.json"
    meta = json.loads(mpath.read_text(encoding="utf-8"))
    osd = meta["original_sample_details"]
    now = {x["id"] for x in orig}
    for k, v in osd.items():
        if k not in now:
            v["role_c_status"] = "2026-10-05 역할 C 점검에서 삭제(상품명이 점으로 가려져 광고 내용이 없음). 기록용으로 남김"
    for x in orig:
        if x["id"] in osd:
            continue
        m = re.search(r'href="([^"]+)"', x["html"])
        osd[x["id"]] = {"previous_record": {
            "id": x["id"], "category": "OFFSCREEN", "subtype": x["subtype"], "evidence_text": x["evidence_text"], "html": x["html"],
            "source": x["source"], "source_host": urlparse(x["source"]).netloc, "source_publisher": new_publisher,
            "source_publisher_key": new_publisher, "ad_href": m.group(1) if m else None, "evidence_basis": "historical_copied_original",
            "review_status": "role_c_added_historical_copied_original", "is_positive": True, "collected_on": TODAY,
            "added_by": "역할 C (2026-10-06 visibility_hidden 보충)", "notes": x["notes"]},
            "expected_location_scope": "html 발췌 기준", "excerpt_selector_match_count": 1}
    dump(mpath, meta)

    def publisher(x):
        return osd[x["id"]]["previous_record"].get("source_publisher_key") or osd[x["id"]]["previous_record"].get("source_publisher")

    def basis(x):
        return osd[x["id"]]["previous_record"].get("evidence_basis")

    # 2. 렌더링
    res = render_all({"orig": orig, "fixt": fixt, "ctrl": ctrl})
    vps = list(VIEWPORTS)

    def runs(name, xs, cond):
        return sum(1 for x in xs for vp in vps if cond(res[(name, vp, x["id"])]))

    uniq = lambda r: r.get("count") == 1 and r.get("text_ok")  # noqa: E731
    hidden = lambda r: r.get("count") == 1 and r.get("hidden")  # noqa: E731
    visible = lambda r: r.get("count") == 1 and not r.get("hidden")  # noqa: E731
    counts = {s: Counter(x["subtype"] for x in orig)[s] for s in SUBTYPES}
    fcounts = {s: Counter(x["subtype"] for x in fixt)[s] for s in SUBTYPES}
    quotas = {"font_left_display": 45, "visibility_hidden": 15, "clip": 15, "text_indent": 10, "transform_outside": 15}
    pubs = Counter(publisher(x) for x in orig)
    tiny = sum(1 for x in fixt if any("font-size" in w for w in res[("fixt", "desktop", x["id"])].get("why", [])))
    net = sum(res[("_net", vp)] for vp in vps)
    errs = [e for vp in vps for e in res[("_err", vp)]]

    vpath, spath = B / "검증결과.json", B / "최종현황.json"
    v = json.loads(vpath.read_text(encoding="utf-8"))
    s = json.loads(spath.read_text(encoding="utf-8"))
    first_v = {k: v[k] for k in ("approved_originals", "approved_original_counts", "fixture_count", "viewport_runs",
                                  "unique_selector_and_exact_text_checks", "positive_fixture_rendering_passed",
                                  "negative_controls_visible_passed", "tiny_font_positive_fixtures")}
    all_ok = (runs("orig", orig, uniq) == len(orig) * 2 and runs("fixt", fixt, uniq) == len(fixt) * 2 and runs("ctrl", ctrl, uniq) == len(ctrl) * 2
              and runs("orig", orig, hidden) == len(orig) * 2 and runs("fixt", fixt, hidden) == len(fixt) * 2
              and runs("ctrl", ctrl, visible) == len(ctrl) * 2 and net == 0 and not errs)
    v.update({
        "status": "passed" if all_ok else "failed",
        "approved_originals": len(orig),
        "approved_original_counts": counts,
        "original_quota_completed": counts == quotas,
        "source_publisher_cap_passed": max(pubs.values()) <= 10,
        "fixture_count": len(fixt),
        "visible_controls": len(ctrl),
        "viewport_runs": (len(fixt) + len(ctrl)) * 2,
        "unique_selector_and_exact_text_checks": runs("fixt", fixt, uniq) + runs("ctrl", ctrl, uniq),
        "positive_fixture_rendering_passed": runs("fixt", fixt, hidden),
        "negative_controls_visible_passed": runs("ctrl", ctrl, visible),
        "tiny_font_positive_fixtures": tiny,
        "network_requests": net,
        "page_errors": errs,
        "original_excerpt_rendering": {"runs": len(orig) * 2, "unique_selector_and_exact_text": runs("orig", orig, uniq),
                                       "positive_hidden": runs("orig", orig, hidden)},
        "role_c_revision": {
            "date": TODAY, "by": "역할 C",
            "method": "tools/build/refresh_offscreen_meta.py: html+css 만 띄움(JS 끔, 네트워크 막음), Edge(Chromium) 데스크톱 1280x900·모바일 390x844, DPR1",
            "changes": "2026-10-05 상품명이 가려진 원문 7개와 그 시험용 7개 삭제, 숨김이 재현되지 않던 원문 45개 수정, subtype 5종 통일. "
                       "2026-10-06 visibility_hidden 원문 OF-208~214 와 시험용 OF-215~221 보충. 자세한 것은 변경요약_20261005.md",
            "first_edition_values": first_v},
    })
    v["caveats"] = v.get("caveats", []) + [
        "2026-10-06 역할 C 재검증: 원문 100개는 html 발췌만으로 숨김이 재현됨을 확인했다(10-05 에 감싸는 요소를 재구성한 원문은 그 태그가 원문이 아님, notes 참고). 피해 당시 전체 화면 재현은 여전히 아니다.",
        "human_review_rows·review_file_sha256 은 사람 3 의 검수 CSV(102행) 기준이다. 10-06 보충 7개는 그 CSV 에 없고 역할 C 가 원문 게시글을 확인해 넣었다."]
    for key in ("sample_schema_alignment", "original_sample_schema_alignment"):
        if key in v:
            v[key]["role_c_note"] = f"{TODAY}: 이 항목은 사람 3 첫 판(원문 OF-108~207, 시험용 OF-001~100) 기준 기록이다. 지금 id 는 원문 OF-108~214(삭제 7개 제외), 시험용 OF-001~100(삭제 7개 제외)·OF-215~221, 대조군 OF-101~107"
    dump(vpath, v)

    first_s = {k: s.get(k) for k in ("approved_original_counts", "source_publisher_counts", "original_evidence_basis_counts",
                                      "fixture_counts", "js_visibility_and_display_combined_originals", "redacted_original_text_ids")}
    redacted_left = [osd[x["id"]]["previous_record"]["id"] for x in orig
                     if osd[x["id"]]["previous_record"]["id"] in (first_s["redacted_original_text_ids"] or [])]
    s.update({
        "quota_originals": len(orig),
        "approved_original_counts": counts,
        "original_shortage": {k: max(0, quotas[k] - counts[k]) for k in quotas},
        "original_quota_completed": counts == quotas,
        "original_evidence_basis_counts": dict(Counter(basis(x) for x in orig)),
        "source_publisher_counts": dict(pubs),
        "controlled_css_fixtures": len(fixt),
        "visible_controls": len(ctrl),
        "fixture_counts": fcounts,
        "js_visibility_and_display_combined_originals": sum(1 for x in orig if "visibility:hidden; display:none" in x["html"]),
        "redacted_original_text_ids": redacted_left,
        "fixture_rendering_verified": all_ok,
        "role_c_revision": {"date": TODAY, "by": "역할 C", "first_edition_values": first_s,
                            "note": "total_human_approved·reference_only·review_file_sha256 은 사람 3 검수 CSV 기준 그대로다. 10-06 보충 7개는 역할 C 가 넣었다. "
                                    "redacted_original_text_ids 는 지금 원문 중 상품명 일부가 점으로 가려진 것(OF-165 levitra vs .)만 남겼다."},
    })
    dump(spath, s)

    # 3. SHA256
    hpath = B / "패키지_SHA256.json"
    old = json.loads(hpath.read_text(encoding="utf-8"))
    files = {p.relative_to(B).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
             for p in B.rglob("*") if p.is_file() and p.name != hpath.name and "__pycache__" not in p.parts}
    keep_raw = {k: h for k, h in old.items() if k.startswith("data/raw/") and k not in files}
    new = dict(sorted({**files, **keep_raw}.items()))
    dump(hpath, new)

    print("검증", v["status"], "| 원문", v["original_excerpt_rendering"], "| 시험용 숨김", v["positive_fixture_rendering_passed"], "/", len(fixt) * 2,
          "| 대조군 보임", v["negative_controls_visible_passed"], "/", len(ctrl) * 2, "| 선택자·문구", v["unique_selector_and_exact_text_checks"],
          "| 네트워크", net, "| 오류", len(errs))
    print("분류", counts, "| 근거", s["original_evidence_basis_counts"], "| 최다 출처", pubs.most_common(3))
    print("SHA", len(new), "(지금 파일", len(files), "+ data/raw 유지", len(keep_raw), ") | 뺀 항목", sorted(set(old) - set(new)))


if __name__ == "__main__":
    main(*sys.argv[1:3])
