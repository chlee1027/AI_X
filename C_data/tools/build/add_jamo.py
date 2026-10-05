"""JAMO 샘플 덧붙이기 (2026-10-06, 역할 C).

fix_jamo.py 로 정리한 jamo.yaml 의 기존 id 는 그대로 두고, 새 항목을 끝에 붙여 이어지는 번호(JM-143 …)를 매긴다.
- html 은 evidence 를 감싼 <span id="jm-NNN"> 으로 다시 만들고 expected_location 을 맞춘다
- 공백을 무시한 evidence 가 기존과 같으면 멈춘다
- 전화번호 꼴(010 + 숫자 7~8자리)이 드러나 있으면 멈춘다 (가림 규칙)
사용: python tools/build/add_jamo.py data/samples/jamo.yaml add.yaml
"""
import html
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

PHONE = re.compile(r"0\s*1\s*0\D{0,3}\d{3,4}\D{0,3}\d{4}")


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def main(path: str, add: str) -> None:
    rows = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    new = yaml.safe_load(Path(add).read_text(encoding="utf-8"))
    have = {norm(x["evidence_text"]) for x in rows}
    n = max(int(x["id"].split("-")[1]) for x in rows) + 1
    for x in new:
        ev = x["evidence_text"]
        assert norm(ev) not in have, f"중복: {ev[:40]}"
        assert not PHONE.search(ev), f"전화번호 드러남: {ev[:40]}"
        have.add(norm(ev))
        x["id"] = f"JM-{n:03d}"
        x["html"] = f'<span id="jm-{n:03d}">{html.escape(ev, quote=False)}</span>'
        x["expected_location"] = f"#jm-{n:03d}"
        rows.append(x)
        n += 1
    Path(path).write_text(yaml.safe_dump(rows, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
    print(len(rows), Counter(x["subtype"] for x in rows), [x["id"] for x in new])


if __name__ == "__main__":
    main(*sys.argv[1:3])
