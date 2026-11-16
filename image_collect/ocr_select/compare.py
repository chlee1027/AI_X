"""OCR 엔진 비교: 합성 배너(make_synth.py)에서 글자 오류율(CER)과 이미지당 시간을 잰다.

CER = 편집 거리 / 정답 글자 수. 비교 전에 양쪽을 NFKC 로 맞추고, 소문자로 바꾸고, 빈칸을 모두 지운다
(글상자를 잇는 순서·빈칸 차이는 판정기 입력에 영향이 작고, 엔진마다 띄어쓰기 방식이 달라 공정하지 않기 때문).
엔진 하나당 첫 이미지 1장은 준비(모델 적재) 시간이 섞이므로 시간 통계에서 뺀다.
출력: ocr_select/result_<engine>.csv(이미지별), 표준 출력에 언어별·전체 요약
사용: python compare.py easyocr paddleocr
"""
import csv
import os
import statistics
import sys
import time
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "tools"))
from ocr_engines import ENGINES  # noqa: E402


def norm(s):
    return "".join(unicodedata.normalize("NFKC", s).lower().split())


def edit(a, b):
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def main(names):
    gt = list(csv.DictReader(open(os.path.join(HERE, "synth_gt.csv"), encoding="utf-8")))
    for name in names:
        t0 = time.time()
        eng = ENGINES[name]()
        load_s = time.time() - t0
        rows = []
        for k, g in enumerate(gt):
            t = time.time()
            r = eng.run(os.path.join(HERE, "synth", g["id"] + ".jpg"))
            dt = time.time() - t
            a, b = norm(g["text"]), norm(r["text"])
            rows.append(dict(id=g["id"], lang=g["lang"], source=g["source"], gt=g["text"], pred=r["text"],
                             cer=round(edit(a, b) / max(1, len(a)), 4), exact=int(a == b), sec=round(dt, 3), first=int(k == 0)))
        with open(os.path.join(HERE, f"result_{name}.csv"), "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"== {name} {eng.version}  모델 적재 {load_s:.1f}s")
        for grp in ["ko", "mixed", "en", "ALL"]:
            sub = [r for r in rows if grp == "ALL" or r["lang"] == grp]
            if not sub:
                continue
            cers = [r["cer"] for r in sub]
            print(f"  {grp:5s} n={len(sub):3d}  CER 평균 {statistics.mean(cers):.3f}  중앙 {statistics.median(cers):.3f}  "
                  f"완전 일치 {sum(r['exact'] for r in sub)}/{len(sub)}")
        secs = [r["sec"] for r in rows if not r["first"]]
        print(f"  시간: 이미지당 평균 {statistics.mean(secs):.2f}s, 중앙 {statistics.median(secs):.2f}s (첫 장 제외 {len(secs)}장, CPU)")


if __name__ == "__main__":
    main(sys.argv[1:] or ["easyocr", "paddleocr"])
