"""이미지 복사본을 찾아 지운다.

사용: python dedup.py plan   -> logs/dedup_plan.csv 를 쓴다 (아무것도 안 지운다)
      python dedup.py apply  -> plan 대로 지우고 기록을 고친다

복사본 판정 (모두 만족):
  1) pHash 거리 4 이하, 가로세로비 차이 2% 이하
  2) 같은 크기로 줄여 비교한 픽셀 차이의 99 백분위가 16 이하 (0~255)
  3) 작은 창(짧은 변의 1/16)으로 훑은 평균 차이의 최댓값이 20 미만 (12병/24병 같은 작은 표시 차이를 잡는다)
  4) OCR 글의 숫자와 @아이디가 양쪽에 있으면 서로 같다 (OCR 오독이면 복사본이 남는 쪽으로 틀린다)
  5) 라벨이 둘 다 있으면 label, category 가 같다
남길 파일: 기존 라벨 > 추가 라벨 > 라벨 없음, 그다음 애매 아닌 것, 그다음 큰 것.
지운 복사본의 수집 기록은 남길 파일로 옮겨, 같은 그림이 어느 사이트에 있었는지 잃지 않는다.
"""
import csv
import glob
import hashlib
import json
import os
import re
import shutil
import sys
from collections import Counter, defaultdict

import imagehash
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
COL = os.path.join(ROOT, "collect")
IMG = os.path.join(COL, "images")
PLAN = os.path.join(ROOT, "logs", "dedup_plan.csv")
BACK = os.path.join(ROOT, "logs", "dedup_backup")
Q_MAX = 16
B_MAX = 20
csv.field_size_limit(10**8)


def rd(path):
    with open(path, encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        return list(r), r.fieldnames


def wr(path, rows, cols):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, cols)
        w.writeheader()
        w.writerows(rows)
    os.replace(tmp, path)


def labels():
    lab = {}
    for fn, src in (("labels_draft.csv", 0), ("labels_draft_add.csv", 1)):
        for r in rd(os.path.join(COL, fn))[0]:
            lab[r["file"]] = (src, r["label"], r["category"], r["unsure"])
    return lab


def contacts(s):
    return set(re.findall(r"\d+", s or "")) | {m.lower() for m in re.findall(r"@\w{3,}", s or "")}


def plan():
    files = sorted(f for f in os.listdir(IMG) if ".tmp" not in f)
    ims, ph = {}, {}
    for f in files:
        with Image.open(os.path.join(IMG, f)) as im:
            im.seek(0)
            r = im.convert("RGB")
        ims[f] = r.size
        ph[f] = int(str(imagehash.phash(r)), 16)
    A = np.array([ph[f] for f in files], dtype=np.uint64)
    pc = np.array([bin(i).count("1") for i in range(65536)], dtype=np.uint8)
    M = np.uint64(0xffff)

    def ham(x, Y):
        z = np.bitwise_xor(Y, x)
        return pc[z & M] + pc[(z >> np.uint64(16)) & M] + pc[(z >> np.uint64(32)) & M] + pc[(z >> np.uint64(48)) & M]

    cache = {}

    def load(f):
        if f not in cache:
            if len(cache) > 3000:
                cache.pop(next(iter(cache)))
            with Image.open(os.path.join(IMG, f)) as im:
                im.seek(0)
                cache[f] = im.convert("RGB")
        return cache[f]

    def diff(a, b, local=False):
        sa, sb = ims[a], ims[b]
        ra, rb = sa[0] / sa[1], sb[0] / sb[1]
        if abs(ra - rb) / max(ra, rb) > 0.02:
            return None
        w = min(sa[0], sb[0], 256)
        h = max(1, round(w / ra))
        x = np.asarray(load(a).resize((w, h), Image.LANCZOS), dtype=np.int16)
        y = np.asarray(load(b).resize((w, h), Image.LANCZOS), dtype=np.int16)
        d = np.abs(x - y).max(axis=2).astype(np.float64)
        q = float(np.percentile(d, 99))
        if not local:
            return q
        k = max(4, min(w, h) // 16)
        if h < k or w < k:
            return q, float(d.mean())
        c = np.pad(d.cumsum(0).cumsum(1), ((1, 0), (1, 0)))
        return q, float(((c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]) / (k * k)).max())

    p = list(range(len(files)))

    def find(x):
        while p[x] != x:
            p[x] = p[p[x]]
            x = p[x]
        return x

    for i in range(len(files)):
        d = ham(A[i], A[i + 1:])
        for j in np.nonzero(d <= 4)[0]:
            k = i + 1 + int(j)
            q = diff(files[i], files[k])
            if q is not None and q <= Q_MAX:
                p[find(i)] = find(k)
    groups = defaultdict(list)
    for i, f in enumerate(files):
        groups[find(i)].append(f)

    lab = labels()
    ocr = {}
    for f in glob.glob(os.path.join(COL, "ocr_raw*.csv")):
        for r in rd(f)[0]:
            ocr[r["file"]] = r["text"]

    def rank(f):
        s = ims[f]
        l = lab.get(f)
        return (l[0] if l else 2, 0 if not l or l[3] != "1" else 1, -s[0] * s[1], f)

    rows, kept_back = [], Counter()
    for v in groups.values():
        if len(v) < 2:
            continue
        keep = min(v, key=rank)
        ck, lk = contacts(ocr.get(keep)), lab.get(keep)
        for f in v:
            if f == keep:
                continue
            res = diff(keep, f, local=True)
            if res is None or res[0] > Q_MAX:
                kept_back["체인으로만 연결"] += 1
                continue
            q, b = res
            if b >= B_MAX:
                kept_back["작은 영역이 다름"] += 1
                continue
            cf = contacts(ocr.get(f))
            if ck and cf and ck != cf:
                kept_back["OCR 숫자·아이디가 다름"] += 1
                continue
            lf = lab.get(f)
            if lk and lf and lk[1:3] != lf[1:3]:
                kept_back["라벨이 다름"] += 1
                continue
            rows.append({"removed": f, "kept": keep, "q99": round(q, 1), "block": round(b, 1),
                         "removed_size": f"{ims[f][0]}x{ims[f][1]}", "kept_size": f"{ims[keep][0]}x{ims[keep][1]}",
                         "removed_label": "/".join(lf[1:]) if lf else "", "kept_label": "/".join(lk[1:]) if lk else "",
                         "removed_from": ("base" if lf[0] == 0 else "add") if lf else ""})
    wr(PLAN, rows, list(rows[0]))
    print("지울 파일", len(rows), "남기는 파일 수(묶음)", len({r["kept"] for r in rows}), "제외", dict(kept_back))
    print("지울 파일 라벨", Counter(r["removed_label"].split("/")[0] + "/" + r["removed_from"] for r in rows))
    print("불법 종류별", Counter(r["removed_label"].split("/")[1] for r in rows if r["removed_label"].startswith("illegal")))


def apply():
    rows = rd(PLAN)[0]
    m = {r["removed"]: r["kept"] for r in rows}
    assert not set(m) & set(m.values()), "남길 파일이 지울 목록에 있다"
    os.makedirs(BACK, exist_ok=True)
    sha = {}
    for k in set(m.values()):
        with open(os.path.join(IMG, k), "rb") as f:
            sha[k] = hashlib.sha1(f.read()).hexdigest()
    # 1 수집 기록: 같은 페이지 위치의 겹친 줄을 지우고, 지울 파일의 기록은 남길 파일로 옮긴다
    n_dup = n_move = 0
    seen = set()
    for f in sorted(glob.glob(os.path.join(COL, "occurrences_*.csv"))):
        data, cols = rd(f)
        out, changed = [], False
        for r in data:
            key = (r["sha1"], r["page_url"], r["source_url"], r["selector"], r["x"], r["y"])
            if key in seen:
                n_dup += 1
                changed = True
                continue
            seen.add(key)
            base = os.path.basename(r["file"])
            if base in m:
                r["file"] = r["file"][: -len(base)] + m[base]
                r["sha1"] = sha[m[base]]
                n_move += 1
                changed = True
            out.append(r)
        if changed:
            shutil.copy2(f, BACK)
            wr(f, out, cols)
    # 2 라벨
    for fn in ("labels_draft.csv", "labels_draft_add.csv"):
        path = os.path.join(COL, fn)
        data, cols = rd(path)
        shutil.copy2(path, BACK)
        wr(path, [r for r in data if r["file"] not in m], cols)
    # 3 OCR
    for f in glob.glob(os.path.join(COL, "ocr_raw*.csv")):
        data, cols = rd(f)
        out = [r for r in data if r["file"] not in m]
        if len(out) != len(data):
            shutil.copy2(f, BACK)
            wr(f, out, cols)
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
    # 4 그림 파일 (기록을 다 고친 뒤 마지막에)
    for f in m:
        os.remove(os.path.join(IMG, f))
    print("지운 파일", len(m), "겹친 기록 줄", n_dup, "옮긴 기록 줄", n_move, "남은 파일", len(os.listdir(IMG)))


if __name__ == "__main__":
    {"plan": plan, "apply": apply}[sys.argv[1]]()
