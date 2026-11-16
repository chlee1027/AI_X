"""11.6 관문 집계: R_pos(실제 불법광고 이미지) 몇 장인가.

입력: collect/labels_draft.csv (file, label, category, unsure, lang, note) 와 collect/occurrences_*.csv
두 가지 수를 낸다.
  (가) 내용이 같은 파일을 하나로 친 수(SHA-1 기준. 명세 3절 image_id 규칙과 같다)
  (나) pHash 해밍 거리 <= 8 인 것끼리 이은 묶음 수(크기만 다르거나 살짝 잘린 같은 배너를 하나로 침. 명세 10절 제안 문턱)
관문 문구 「중복 제거 후」는 (가)로 읽는 것이 명세 3절과 맞고, (나)는 실제로 서로 다른 배너가 몇 개인지 보여 주는 보조 수다.
출처 사이트 수(등록 도메인)도 같이 센다(목표 20곳 이상).
"""
import csv
import glob
import os
from collections import Counter, defaultdict

import imagehash
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
COL = os.path.join(HERE, "..", "collect")


def main():
    lab = {r["file"]: r for r in csv.DictReader(open(os.path.join(COL, "labels_draft.csv"), encoding="utf-8"))}
    occ = defaultdict(list)
    for f in glob.glob(os.path.join(COL, "occurrences_*.csv")):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            occ[os.path.basename(r["file"])].append(r)
    pos = [f for f, r in lab.items() if r["label"] == "illegal"]
    sure = [f for f in pos if lab[f]["unsure"] != "1"]
    print("라벨 붙인 이미지", len(lab), Counter(r["label"] for r in lab.values()))
    print("illegal (가) 같은 파일 하나로:", len(pos), " 그중 unsure=0:", len(sure))
    hashes = {f: imagehash.phash(Image.open(os.path.join(COL, "images", f)).convert("RGB")) for f in pos}
    parent = {f: f for f in pos}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for i, a in enumerate(pos):
        for b in pos[i + 1:]:
            if hashes[a] - hashes[b] <= 8:
                parent[find(a)] = find(b)
    groups = Counter(find(f) for f in pos)
    print("illegal (나) pHash<=8 묶음 수:", len(groups), " 가장 큰 묶음:", groups.most_common(1)[0][1] if groups else 0)
    sites = Counter()
    for f in pos:
        for s in {o["site"] for o in occ.get(f, [])}:
            sites[s] += 1
    print("illegal 출처 사이트 수:", len(sites))
    for s, n in sites.most_common():
        print(f"  {s}: {n}")
    print("category:", Counter(lab[f]["category"] for f in pos))
    print("lang:", Counter(lab[f]["lang"] for f in pos))


if __name__ == "__main__":
    main()
