"""labels_add.py 의 판·칸 표기 -> collect/labels_draft_add.csv (labels_draft.csv 와 같은 열, source=ADD, labeler=Claude초안).

labels_draft.csv 는 건드리지 않고 거기 있는 파일은 다시 적지 않는다. 뉴스·쇼핑·금융·병원·공공 씨앗 이미지가 낱말 오탐으로 후보에 들어온 것은
불법·합법 광고·계도로 적은 칸만 라벨을 남기고 나머지는 라벨 없는 일반 후보로 둔다.
"""
import glob
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import csv  # noqa: E402

import safe_io  # noqa: E402
from build_labels import lang_of  # noqa: E402
from labels_add import ADD  # noqa: E402

COL = os.path.join(HERE, "..", "collect")
SHEETS = os.path.join(HERE, "..", "logs", "sheets")
GEN = {"news", "shopping", "finance", "hospital", "public"}


def main():
    idx = {}
    for f in glob.glob(os.path.join(SHEETS, "N*_index.csv")):
        for r in safe_io.read_csv(f):
            idx[(r["sheet"], int(r["cell"]))] = r["file"]
    base = {r["file"] for r in safe_io.read_csv(os.path.join(COL, "labels_draft.csv"))}
    ocr = {}
    for f in glob.glob(os.path.join(COL, "ocr_raw*.csv")):
        for r in safe_io.read_csv(f):
            ocr[r["file"]] = r["text"]
    stype = {}
    for f in glob.glob(os.path.join(COL, "occurrences_*.csv")):
        for r in safe_io.read_csv(f):
            stype.setdefault(os.path.basename(r["file"]), r["site_type"])
    out = []
    seen = set(base)
    for sheet, d in ADD.items():
        for (s, c) in sorted(k for k in idx if k[0] == sheet):
            fn = idx[(s, c)]
            if fn in seen:
                continue
            seen.add(fn)
            if c in d.get("S", {}):
                lab = ("illegal", d["S"][c], 0)
            elif c in d.get("U", {}):
                lab = ("illegal", d["U"][c], 1)
            elif c in d.get("LS", []):
                lab = ("legal_ad", "", 0)
            elif c in d.get("LC", []):
                lab = ("campaign", "", 0)
            elif c in d.get("OU", []):
                lab = ("other", "", 1)
            elif stype.get(fn) in GEN:
                continue
            else:
                lab = ("other", "", 0)
            out.append(dict(file=fn, label=lab[0], category=lab[1], unsure=lab[2], lang=lang_of(ocr.get(fn, "")), labeler="Claude초안", source="ADD"))
    with open(os.path.join(COL, "labels_draft_add.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "label", "category", "unsure", "lang", "labeler", "source"])
        w.writeheader()
        w.writerows(out)
    print(len(out), Counter((r["label"], r["category"], r["unsure"]) for r in out).most_common())


if __name__ == "__main__":
    main()
