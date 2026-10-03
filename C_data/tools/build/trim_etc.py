"""ETC 를 정해진 개수로 맞춘다: 넘치는 만큼 가장 흔한 하위 유형에서, 항목이 가장 많은 사이트부터 하나씩 뺀다.

드문 하위 유형(meta·encoding·link)은 건드리지 않고, 한 사이트가 데이터를 덮는 쏠림을 줄이는 방향으로만 뺀다.
사용: python trim_etc.py in.yaml out.yaml 200
"""
import re
import sys
from collections import Counter
from pathlib import Path

import yaml


def host(x: dict) -> str:
    m = re.search(r"https?://([^/ ]+)", x["source"])
    return m.group(1) if m else "doorway"


def main(src: str, out: str, n: str) -> None:
    items = yaml.safe_load(Path(src).read_text(encoding="utf-8"))
    target = int(n)
    while len(items) > target:
        sub = Counter(x["subtype"] for x in items).most_common(1)[0][0]
        per = Counter(host(x) for x in items if x["subtype"] == sub)
        h = per.most_common(1)[0][0]
        # 그 사이트의 그 하위 유형 중 마지막 항목을 뺀다
        idx = max(i for i, x in enumerate(items) if x["subtype"] == sub and host(x) == h)
        items.pop(idx)
    for i, it in enumerate(items, 1):
        it["id"] = f"ET-{i:03d}"
    Path(out).write_text(yaml.safe_dump(items, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
    print(len(items), Counter(x["subtype"] for x in items))
    print("사이트", len({host(x) for x in items}))


if __name__ == "__main__":
    main(*sys.argv[1:4])
