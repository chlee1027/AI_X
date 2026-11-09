"""기록 점검: 페이지 중복, 이미지 파일과 수집 기록 연결, OCR 중복, 수집 기록 중복(전원 차단으로 다시 연 페이지)을 센다."""
import glob
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import safe_io  # noqa: E402

COL = os.path.join(HERE, "..", "collect")
pages = Counter()
for f in glob.glob(os.path.join(COL, "pages_*.csv")):
    pages.update(r["page_url"] for r in safe_io.read_csv(f))
print("페이지 기록", sum(pages.values()), "서로 다른 페이지", len(pages), "두 번 이상 연 페이지", sum(v > 1 for v in pages.values()))
ocr = Counter()
for f in glob.glob(os.path.join(COL, "ocr_raw*.csv")):
    ocr.update(r["file"] for r in safe_io.read_csv(f))
print("OCR 기록", sum(ocr.values()), "서로 다른 파일", len(ocr), "두 번 이상 읽은 파일", sum(v > 1 for v in ocr.values()))
occ = Counter()
linked = set()
for f in glob.glob(os.path.join(COL, "occurrences_*.csv")):
    for r in safe_io.read_csv(f):
        occ[(r["page_url"], r["file"], r["selector"], r["x"], r["y"])] += 1
        if r["page_url"] and r["source_url"]:
            linked.add(os.path.basename(r["file"]))
print("수집 기록", sum(occ.values()), "겹친 기록", sum(v - 1 for v in occ.values() if v > 1))
files = [f for f in os.listdir(os.path.join(COL, "images")) if ".tmp" not in f]
print("이미지 파일", len(files), "수집 기록과 연결", sum(f in linked for f in files), "안 된 것", sum(f not in linked for f in files),
      "크기 0", sum(os.path.getsize(os.path.join(COL, "images", f)) == 0 for f in files))
