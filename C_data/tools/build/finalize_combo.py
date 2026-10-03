"""combo 후보 -> 정해진 개수의 combo_real.yaml.

1. 공백·기호만 다른 같은 글(같은 사이트)을 하나로 합친다 (예: 【BLＧM 7.ＣＯM】 와 【BLＧM   7.ＣＯM】)
2. 넘치면 항목이 가장 많은 사이트부터 하나씩 뺀다 (한 캠페인 쏠림을 줄이는 방향)
3. id 를 CB-001 부터 다시 매긴다

사용: python finalize_combo.py in.yaml out.yaml 200
"""
import re
import sys
from collections import Counter
from pathlib import Path

import yaml


def host(x: dict) -> str:
    return re.search(r"https?://([^/ ]+)", x["source"]).group(1)


def main(src: str, out: str, n: str) -> None:
    xs = yaml.safe_load(Path(src).read_text(encoding="utf-8"))
    seen, items = set(), []
    for x in xs:
        k = (host(x), re.sub(r"[\s\W_]+", "", x["evidence_text"])[:60])
        if k not in seen:
            seen.add(k)
            items.append(x)
    while len(items) > int(n):
        h = Counter(host(x) for x in items).most_common(1)[0][0]
        items.pop(max(i for i, x in enumerate(items) if host(x) == h))
    for i, x in enumerate(items, 1):
        x["id"] = f"CB-{i:03d}"
    Path(out).write_text(yaml.safe_dump(items, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
    c = Counter(host(x) for x in items)
    print(len(xs), "->", len(items), "| 사이트", len(c), c.most_common(5))


if __name__ == "__main__":
    main(*sys.argv[1:4])
