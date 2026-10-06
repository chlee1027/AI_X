"""게이트 검사: 팀 공통 양식 + expected_location이 html에서 요소 1개만 가리키는지 + 원문이 그 요소에 있는지.

사용 예:
    python validate.py data/samples/*.yaml
"""
import html as htmllib
import re
import sys
from collections import Counter
from pathlib import Path

import lxml.html
import yaml

REQUIRED = ["id", "category", "subtype", "html", "css", "evidence_text", "expected_location", "is_positive",
            "extra_finding", "source", "notes"]
CATEGORIES = {"DECOY", "ETC", "HOMOGLYPH", "TRANSPARENT", "OFFSCREEN", "JAMO"}
HG_SUBTYPES = {"fullwidth", "cyrillic_greek", "digit_letter", "partial_token", "fullwidth_symbol", "hangul_lookalike", "enclosed_alnum"}


def norm(s):
    return re.sub(r"\s+", " ", htmllib.unescape(s)).strip()


def check(path):
    rows = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []
    errs, ids = [], Counter(r.get("id") for r in rows)
    for r in rows:
        rid = r.get("id", "?")
        miss = [k for k in REQUIRED if k not in r]
        if miss:
            errs.append(f"{rid}: 필드 누락 {miss}")
            continue
        if ids[rid] > 1:
            errs.append(f"{rid}: id 중복")
        if r["category"] not in CATEGORIES:
            errs.append(f"{rid}: category 값 오류 {r['category']}")
        if r["category"] == "HOMOGLYPH" and r["subtype"] not in HG_SUBTYPES:
            errs.append(f"{rid}: HOMOGLYPH 하위 유형 오류 {r['subtype']}")
        if not isinstance(r["is_positive"], bool):
            errs.append(f"{rid}: is_positive는 true/false")
        if r["category"] == "DECOY" and r["is_positive"]:
            errs.append(f"{rid}: DECOY인데 is_positive=true")
        try:
            root = lxml.html.fromstring(f"<div>{r['html']}</div>")
            found = root.cssselect(r["expected_location"])
        except Exception as e:
            errs.append(f"{rid}: html/선택자 파싱 실패 {e}")
            continue
        if len(found) != 1:
            errs.append(f"{rid}: 선택자 매칭 {len(found)}개 (1개여야 함) → {r['expected_location']}")
            continue
        if norm(r["evidence_text"])[:40] not in norm(found[0].text_content()):
            errs.append(f"{rid}: evidence_text가 해당 요소 안에 없음")
    return rows, errs


def main():
    total_err = 0
    for p in sys.argv[1:]:
        rows, errs = check(p)
        subs = Counter(r.get("subtype") for r in rows)
        status = "통과" if not errs else f"오류 {len(errs)}건"
        print(f"[{status}] {p}: {len(rows)}건 · 하위 유형 {dict(subs)}")
        for e in errs[:30]:
            print("   -", e)
        total_err += len(errs)
    sys.exit(1 if total_err else 0)


if __name__ == "__main__":
    main()
