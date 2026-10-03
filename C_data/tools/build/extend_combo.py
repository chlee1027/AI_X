"""기존 combo_real.yaml 은 그대로 두고, 새 후보를 「안 쏠리게」 덧붙인다.

규칙
  - 기존 항목과 같은 글(같은 사이트, 공백·기호 뺀 앞 60자 같음)은 건너뛴다
  - 기존에 이미 BIG 개 이상 있는 사이트(강화군·인디고게임 캠페인 등)에서는 더 넣지 않는다
  - 새로 넣는 항목은 사이트당 NEW_CAP 개까지
  - 사이트를 돌아가며 하나씩 고른다 (한 사이트가 먼저 몰아 채우지 않게). 같은 사이트 안에서는 수법 조합이 다른 것부터
  - 목표 개수에 닿으면 멈춘다. id 는 기존 뒤에 이어서 매긴다

사용: python extend_combo.py existing.yaml candidates.yaml out.yaml 300 [NEW_CAP=5] [BIG=20]
"""
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml


def host(x: dict) -> str:
    # www.·m.·en. 만 다른 주소는 같은 사이트로 센다 (nebuah.com 과 www.nebuah.com)
    return re.sub(r"^(www|m|en)\.", "", re.search(r"https?://([^/ ]+)", x["source"]).group(1))


# 도박 홍보 사이트 자체(스팸이 올라온 정상 사이트가 아님). 2026-10-04 사이트 이름 「온라인 홀덤사이트 - 인디고게임」 확인 후 제외
GAMBLING_SITES = {"magino.co.kr"}


def key(x: dict) -> tuple:
    # Goodreads 태그 쪽은 제목과 「Quotes tagged as "…"」 두 곳에 같은 문구가 나오므로 그 꾸밈말과 하이픈을 빼고 비교한다
    ev = re.sub(r"Quotes tagged as|Quotes$", "", x["evidence_text"].strip())
    return host(x), re.sub(r"[\s\W_]+", "", ev).lower()[:60]


def main(existing: str, cand: str, out: str, target: str, new_cap: str = "5", big: str = "20") -> None:
    old = [x for x in yaml.safe_load(Path(existing).read_text(encoding="utf-8")) if host(x) not in GAMBLING_SITES]
    cands = yaml.safe_load(Path(cand).read_text(encoding="utf-8"))
    have = {key(x) for x in old}
    per_old = Counter(host(x) for x in old)
    groups = defaultdict(list)
    for x in cands:
        k = key(x)
        if k in have or per_old[k[0]] >= int(big) or k[0] in GAMBLING_SITES:
            continue
        have.add(k)
        groups[k[0]].append(x)
    added, used_combo = [], defaultdict(set)
    n_new = Counter()
    while len(old) + len(added) < int(target) and any(groups.values()):
        for h in sorted(groups):
            if not groups[h] or n_new[h] >= int(new_cap) or len(old) + len(added) >= int(target):
                groups[h] = [] if n_new[h] >= int(new_cap) else groups[h]
                continue
            i = next((j for j, c in enumerate(groups[h]) if c["subtype"] not in used_combo[h]), 0)
            c = groups[h].pop(i)
            used_combo[h].add(c["subtype"])
            n_new[h] += 1
            added.append(c)
    items = old + added
    for i, x in enumerate(items, 1):
        x["id"] = f"CB-{i:03d}"
    Path(out).write_text(yaml.safe_dump(items, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
    print(f"기존 {len(old)} + 새로 {len(added)} = {len(items)} | 새 항목 사이트 {len(n_new)}곳", dict(n_new))
    print("전체 사이트", len({host(x) for x in items}), Counter(host(x) for x in items).most_common(4))


if __name__ == "__main__":
    main(*sys.argv[1:])
