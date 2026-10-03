"""combo_real.yaml 검증: 양식 · 선택자 유일 · evidence 원문 일치 · 적은 특징이 evidence 에 실제로 있는가 · 개인정보 가림.

사용: python validate_combo.py data/samples/combo_real.yaml
"""
import re
import sys
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "analyze"))
import analyze_obf as A  # noqa: E402

FIELDS = ["id", "category", "subtype", "html", "css", "evidence_text", "expected_location", "is_positive",
          "techniques", "label_codes", "extra_findings", "source", "notes"]
# 가리지 않은 번호: 앞 세 자리 꼴 뒤에 숫자(전각·원 숫자 포함)가 7자 이상 남아 있으면 노출
# 구분자에 자모 ㅡ 도 넣는다 (Oloㅡ8359 O6611 꼴, 2026-10-04)
PHONE_RAW = re.compile(r"[0oOⓞ⓪０][\W_ㅡ]{0,3}[1lI①１][\W_ㅡ]{0,3}[0oOⓞ⓪０](?:[\W_ㅡ]{0,3}[\doOlI０-９①-⓿]){7,8}")


def main(path: str) -> int:
    items = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    errs = []
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        ctx = b.new_context(java_script_enabled=False)
        ctx.route("**/*", lambda r: r.abort())
        pg = ctx.new_page()
        for x in items:
            i = x.get("id", "?")
            miss = [f for f in FIELDS if f not in x]
            if miss:
                errs.append(f"{i}: 칸 없음 {miss}")
                continue
            if not re.fullmatch(r"CB-\d{3}", i) or x["is_positive"] is not True or len(x["techniques"]) < 2:
                errs.append(f"{i}: id·is_positive·techniques 형식")
            pg.set_content(f"<!doctype html><html><body>{x['html']}</body></html>")
            r = pg.evaluate("""([loc, ev]) => { const m = document.querySelectorAll(loc);
                if (m.length !== 1) return {n: m.length};
                const has = [...m[0].childNodes].some(n => n.nodeType === 3 && n.nodeValue.trim() === ev);
                return {n: 1, has}; }""", [x["expected_location"], x["evidence_text"]])
            if r["n"] != 1:
                errs.append(f"{i}: 선택자 매칭 {r['n']}개")
            elif not r["has"]:
                errs.append(f"{i}: evidence 가 대상 요소의 텍스트 노드와 다름")
            got = set(A.features(x["evidence_text"])) - {"emoji"}
            # 전화번호를 가린 경우 digit_sub 모양은 X 로 바뀌어 다시 셀 수 없으므로 notes 의 가림 표시로 갈음
            lost = set(x["techniques"]) - got - ({"digit_sub"} if "가림" in x["notes"] else set())
            if lost:
                errs.append(f"{i}: evidence 에서 다시 안 나오는 특징 {sorted(lost)}")
            if PHONE_RAW.search(x["html"]) or PHONE_RAW.search(x["evidence_text"]):
                errs.append(f"{i}: 가리지 않은 전화번호")
        b.close()
    print(f"샘플 {len(items)}개 / 오류 {len(errs)}건")
    for e in errs:
        print("  " + e)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
