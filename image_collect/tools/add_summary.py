"""추가 수집 결과 요약(최종 보고·진행보고서 4.6절용). 라벨은 초안 기준이다."""
import csv
import glob
import os
import re
import statistics as st
import sys
from collections import Counter, defaultdict

import imagehash
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import safe_io  # noqa: E402

COL = os.path.join(HERE, "..", "collect")
base = {r["file"]: r for r in safe_io.read_csv(os.path.join(COL, "labels_draft.csv"))}
add = {r["file"]: r for r in safe_io.read_csv(os.path.join(COL, "labels_draft_add.csv"))}
lab = {**add, **base}
occ = defaultdict(list)
for f in glob.glob(os.path.join(COL, "occurrences_*.csv")):
    for r in safe_io.read_csv(f):
        occ[os.path.basename(r["file"])].append(r)
for v in occ.values():
    v.sort(key=lambda r: r["collected_at"])
pages = []
for f in glob.glob(os.path.join(COL, "pages_*.csv")):
    shard = re.search(r"pages_(\d+)", f).group(1)
    for r in safe_io.read_csv(f):
        r["_shard"] = int(shard)
        pages.append(r)
new_pages = [r for r in pages if r["_shard"] >= 10]
print("새 페이지 기록", len(new_pages), "상태", Counter((r["status"] or "오류").split(":")[0] for r in new_pages).most_common(8))
print("새 페이지 n_new 합", sum(int(r["n_new"] or 0) for r in new_pages), "too_small", sum(int(r["n_small"] or 0) for r in new_pages), "adult 걸러짐", sum(int(r["n_adult"] or 0) for r in new_pages), "차단 iframe", sum(int(r["blocked_iframe"] or 0) for r in new_pages))
print("새 페이지 도메인", len({r["site"] for r in new_pages}), "origin", Counter(r["origin"].split(":")[0].split("_r")[0] for r in new_pages).most_common())
files = [f for f in os.listdir(os.path.join(COL, "images")) if ".tmp" not in f]
print("전체 파일", len(files))
ocr = {}
for f in glob.glob(os.path.join(COL, "ocr_raw*.csv")):
    for r in safe_io.read_csv(f):
        ocr[r["file"]] = r["text"]
print("OCR 읽은 파일", len(ocr), "안 읽은 파일", len(set(files) - set(ocr)))
# 연결 점검
real = sum(any(o["source_url"].startswith("http") and o["page_url"] for o in occ[f]) for f in files)
datauri = sum((not any(o["source_url"].startswith("http") for o in occ[f])) and bool(occ[f]) for f in files)
print("연결: 이미지 주소(http)+페이지 주소", real, "data-uri 만(페이지 주소 있음)", datauri, "기록 없음", sum(not occ[f] for f in files))
# 불법
pos = [f for f, r in lab.items() if r["label"] == "illegal"]
print("불법", len(pos), "애매", sum(lab[f]["unsure"] == "1" for f in pos), "그중 추가", sum(f in add and f not in base for f in pos))
for c in ["gambling", "adult", "loan", "drug", "invest", "forgery", "etc"]:
    fs = [f for f in pos if lab[f]["category"] == c]
    sure = [f for f in fs if lab[f]["unsure"] != "1"]
    sites = {o["site"] for f in fs for o in occ[f]}
    hs = {f: imagehash.phash(Image.open(os.path.join(COL, "images", f)).convert("RGB")) for f in fs}
    p = {f: f for f in fs}

    def find(x):
        while p[x] != x:
            p[x] = p[p[x]]
            x = p[x]
        return x
    for i, a in enumerate(fs):
        for b in fs[i + 1:]:
            if hs[a] - hs[b] <= 8:
                p[find(a)] = find(b)
    contact = defaultdict(set)
    for f in fs:
        t = ocr.get(f, "")
        for m in re.findall(r"01[016789][-.\s]?\d{3,4}[-.\s]?\d{4}", t):
            contact[re.sub(r"\D", "", m)].add(f)
    top = max((len(v) for v in contact.values()), default=0)
    print(f"  {c}: {len(fs)}장(확실 {len(sure)}, 애매 {len(fs) - len(sure)}), 사이트 {len(sites)}, pHash 묶음 {len({find(f) for f in fs})}, 같은 전화번호 최다 {top}장")
sites = Counter()
for f in pos:
    for s in {o["site"] for o in occ[f]}:
        sites[s] += 1
print("불법 사이트", len(sites), [(s, n, f"{n / len(pos):.1%}") for s, n in sites.most_common(5)], "1장 사이트", sum(v == 1 for v in sites.values()))
# 일반
gen = [f for f in files if lab.get(f, {}).get("label", "other") == "other"]
by = defaultdict(list)
for f in gen:
    by[occ[f][0]["site_type"]].append(f)
print("일반 후보", len(gen), "라벨 있는 것", sum(f in lab for f in gen))
for t, fs in sorted(by.items(), key=lambda x: -len(x[1])):
    ds = Counter(occ[f][0]["site"] for f in fs)
    print(f"  {t}: {len(fs)} ({len(fs) / len(gen):.1%}), 도메인 {len(ds)}, 상위 {ds.most_common(3)}")


def med(fs):
    w = [int(occ[f][0]["w"]) for f in fs if str(occ[f][0]["w"]).isdigit()]
    h = [int(occ[f][0]["h"]) for f in fs if str(occ[f][0]["h"]).isdigit()]
    return st.median(w), st.median(h)


print("크기 중앙값 불법", med(pos), "일반", med(gen))
w468 = [f for f in gen if int(occ[f][0]["w"] or 0) >= 468]
print("일반 가로 468 이상", len(w468), "가로세로비 2 이상", sum(int(occ[f][0]["w"]) / max(int(occ[f][0]["h"] or 1), 1) >= 2 for f in w468))
print("추가 라벨 행", len(add), Counter(r["label"] for r in add.values()))
with open(os.path.join(HERE, "..", "logs", "round_status.csv"), encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
print("차례 집계 줄", len(rows))
