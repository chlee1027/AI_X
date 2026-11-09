"""광고 판별에 쓸 내용이 없는 그림을 지운다. 라벨과 상관없이 모든 그림에 같은 규칙을 쓴다.

사용: python quality_filter.py plan   -> logs/quality_plan.csv 를 쓴다 (아무것도 안 지운다)
      python quality_filter.py apply  -> plan 대로 지우고 기록에서 뺀다

지우는 규칙:
  captcha    : 주소·선택자·alt 에 CAPTCHA 낱말이 있고 가로세로 모두 300px 이하
  near_blank : 64px 로 줄였을 때 채널별 표준편차 최댓값이 8 미만 (빈 그림, 자리표시자, 무늬 없는 배경)
  too_small  : 짧은 변 48px 미만 (아이콘)
크기 기준을 더 올리지 않는 이유: 짧은 변 64px 미만의 불법 이미지 대부분이 125x60 같은 실제 도박 로고 배너다.
일반 이미지만 자르면 작은 그림이 전부 불법이 되어 크기 쏠림이 오히려 커진다.
"""
import csv
import glob
import json
import os
import re
import shutil
import sys
from collections import Counter, defaultdict

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from dedup import COL, IMG, ROOT, labels, rd, wr  # noqa: E402

PLAN = os.path.join(ROOT, "logs", "quality_plan.csv")
BACK = os.path.join(ROOT, "logs", "quality_backup")
PAT = re.compile(r"captcha|securimage|seccode|verifycode|authimg|zmSpamFree", re.I)
STD_MAX = 8
SHORT_MIN = 48


def occurrences():
    occ = defaultdict(list)
    for f in glob.glob(os.path.join(COL, "occurrences_*.csv")):
        for r in rd(f)[0]:
            occ[os.path.basename(r["file"])].append(r)
    return occ


def plan():
    lab, occ = labels(), occurrences()
    rows = []
    for f in sorted(os.listdir(IMG)):
        with Image.open(os.path.join(IMG, f)) as im:
            im.seek(0)
            r = im.convert("RGB")
        w, h = r.size
        r.thumbnail((64, 64))
        std = float(np.asarray(r, dtype=np.float32).reshape(-1, 3).std(axis=0).max())
        o = occ.get(f, [])
        why = []
        if w <= 300 and h <= 300 and any(PAT.search(" ".join((x["source_url"], x["selector"], x["alt"]))) for x in o):
            why.append("captcha")
        if std < STD_MAX:
            why.append("near_blank")
        if min(w, h) < SHORT_MIN:
            why.append("too_small")
        if why:
            l = lab.get(f)
            rows.append({"file": f, "reason": "+".join(why), "w": w, "h": h, "std": round(std, 2),
                         "label": "/".join(l[1:]) if l else "", "from": ("base" if l[0] == 0 else "add") if l else "",
                         "site": o[0]["site"] if o else "", "site_type": o[0]["site_type"] if o else "",
                         "source_url": o[0]["source_url"][:200] if o else ""})
    wr(PLAN, rows, list(rows[0]))
    print("지울 파일", len(rows))
    print("이유", Counter(r["reason"] for r in rows).most_common())
    print("라벨", Counter(r["label"].split("/")[0] + "|" + r["from"] for r in rows).most_common())
    print("불법", [(r["file"], r["reason"], r["w"], r["h"], r["label"]) for r in rows if r["label"].startswith("illegal")])
    print("사이트 종류", Counter(r["site_type"] for r in rows).most_common())


def drop_csv(path, m):
    data, cols = rd(path)
    out = [r for r in data if os.path.basename(r["file"]) not in m]
    if len(out) != len(data):
        shutil.copy2(path, BACK)
        wr(path, out, cols)
    return len(data) - len(out)


def apply():
    m = {r["file"] for r in rd(PLAN)[0]}
    os.makedirs(BACK, exist_ok=True)
    n = Counter()
    for f in glob.glob(os.path.join(COL, "occurrences_*.csv")):
        n["기록 줄"] += drop_csv(f, m)
    for fn in ("labels_draft.csv", "labels_draft_add.csv"):
        n["라벨"] += drop_csv(os.path.join(COL, fn), m)
    for f in glob.glob(os.path.join(COL, "ocr_raw*.csv")):
        n["OCR"] += drop_csv(f, m)
    for f in glob.glob(os.path.join(COL, "ocr_boxes*.jsonl")):
        with open(f, encoding="utf-8", newline="") as h:
            lines = h.readlines()
        out = [l for l in lines if not l.strip() or json.loads(l)["file"] not in m]
        if len(out) != len(lines):
            shutil.copy2(f, BACK)
            tmp = f + ".tmp"
            with open(tmp, "w", encoding="utf-8", newline="") as h:
                h.writelines(out)
            os.replace(tmp, f)
    for f in m:
        os.remove(os.path.join(IMG, f))
    print("지운 파일", len(m), dict(n), "남은 파일", len(os.listdir(IMG)))


if __name__ == "__main__":
    {"plan": plan, "apply": apply}[sys.argv[1]]()
