"""B1·B1+·M3 공통: 데이터 읽기, 채점, 예측 파일·실험 로그 쓰기.

재계획 4절 규칙을 코드로 막는다.
- 평가(test) 몫은 읽지 않는다. load() 는 split 이 train·val 인 행만 돌려준다(--allow-test 는 준아의 평가셋 추론 노트북 전용).
- 양성은 label == illegal 이고 unsure == 1 은 학습·채점에서 뺀다(준아 score.py 와 같은 규칙).
- 문턱값은 검증셋에서만 정한다.

입력 파일(H4 로 돌려받는 것):
  split_v1.csv : image_id, split, group_id
  meta.csv     : image_id, label, unsure, site_type, ... (채현 meta 와 정연 hard/meta_hard.csv 를 함께 줄 수 있다)
  ocr.csv      : image_id, text, ...                     (채현 ocr.csv 와 정연 hard/ocr_hard.csv 를 함께 줄 수 있다)
"""
import csv
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from sklearn.metrics import average_precision_score, precision_recall_fscore_support

HERE = Path(__file__).resolve().parent
PRED_COLS = ["image_id", "score", "pred", "model_id", "config_hash", "commit"]
LOG_COLS = ["exp_id", "date", "model_id", "config", "config_hash", "seed", "split", "n", "n_pos",
            "precision", "recall", "f1", "pr_auc", "threshold", "commit", "memo"]


# ---------- 설정 ----------
def load_config(path):
    """YAML 설정과 그 해시(파일 내용 SHA-1 앞 12자리)를 돌려준다."""
    raw = Path(path).read_bytes()
    return yaml.safe_load(raw.decode("utf-8")), hashlib.sha1(raw).hexdigest()[:12]


def git_commit():
    try:
        out = subprocess.run(["git", "-C", str(HERE), "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=10)
        dirty = subprocess.run(["git", "-C", str(HERE), "status", "--porcelain", "--", str(HERE)], capture_output=True, text=True, timeout=10)
        c = out.stdout.strip() or "nogit"
        return c + ("+dirty" if dirty.stdout.strip() else "")
    except Exception:
        return "nogit"


# ---------- 데이터 ----------
def _read_many(paths):
    frames = [pd.read_csv(p, dtype=str, keep_default_na=False) for p in paths]
    df = pd.concat(frames, ignore_index=True)
    dup = df["image_id"][df["image_id"].duplicated()]
    if len(dup):
        raise SystemExit(f"image_id 중복 {len(dup)}개 (예: {list(dup[:3])}). 같은 파일을 두 번 준 것인지 확인")
    return df


def load(split_path, meta_paths, ocr_paths, allow_test=False):
    """split·meta·ocr 를 image_id 로 합친다. 열: image_id, split, group_id, label, unsure, site_type, text, y, scored."""
    sp = pd.read_csv(split_path, dtype=str, keep_default_na=False)[["image_id", "split", "group_id"]]
    if not allow_test:
        n_test = int((sp["split"] == "test").sum())
        sp = sp[sp["split"].isin(["train", "val"])]
        if n_test:
            print(f"[알림] split_v1 에 test 행 {n_test}개가 있어 읽지 않았다")
    meta = _read_many(meta_paths)
    # H4 의 meta_trainval.csv 처럼 meta 에 split·group_id 가 함께 들어 있으면 split 파일이 정본이다.
    # 값이 split 파일과 하나라도 다르면 멈추고, 같으면 meta 쪽 열을 버린다(합칠 때 split_x·split_y 로 갈리지 않게).
    dup = [c for c in ("split", "group_id") if c in meta.columns]
    if dup:
        chk = sp.merge(meta[["image_id"] + dup], on="image_id", how="inner", suffixes=("", "_meta"))
        for c in dup:
            bad = int((chk[c] != chk[c + "_meta"]).sum())
            if bad:
                raise SystemExit(f"meta 의 {c} 가 split 파일과 다른 행 {bad}개")
        meta = meta.drop(columns=dup)
    ocr = _read_many(ocr_paths)[["image_id", "text"]]
    df = sp.merge(meta, on="image_id", how="left", validate="1:1")
    miss = df["label"].isna().sum() if "label" in df else len(df)
    if miss:
        raise SystemExit(f"meta 에 없는 image_id {miss}개")
    df = df.merge(ocr, on="image_id", how="left", validate="1:1")
    n_no = int(df["text"].isna().sum())
    if n_no:
        print(f"[알림] OCR 행이 없는 이미지 {n_no}개는 빈 글자로 둔다")
    df["text"] = df["text"].fillna("")
    df["unsure"] = df.get("unsure", "0").replace("", "0")
    df["y"] = (df["label"] == "illegal").astype(int)
    df["scored"] = df["unsure"] != "1"
    return df.reset_index(drop=True)


def describe(df):
    for s, g in df.groupby("split"):
        if s == "test":
            # 평가 몫은 장 수만 낸다. 양성·unsure 수는 라벨이라 노트북 출력에 남기지 않는다(출력이 채현에게 넘어올 수 있다)
            print(f"  {s}: {len(g)}장")
            continue
        sc = g[g["scored"]]
        print(f"  {s}: {len(g)}장, 채점 대상 {len(sc)}장, 양성 {int(sc['y'].sum())}장 ({sc['y'].mean():.3f})")


# ---------- 채점 ----------
def best_threshold(y, s):
    """검증셋 F1 이 가장 큰 문턱값(점수 값 중 하나)."""
    y, s = np.asarray(y), np.asarray(s, dtype=float)
    best = (-1.0, 0.5)
    for t in np.unique(s):
        p = (s >= t).astype(int)
        _, _, f, _ = precision_recall_fscore_support(y, p, average="binary", zero_division=0)
        if f > best[0]:
            best = (f, float(t))
    return best[1]


def metrics(y, s, thr):
    y, s = np.asarray(y), np.asarray(s, dtype=float)
    p = (s >= thr).astype(int)
    pr, rc, f, _ = precision_recall_fscore_support(y, p, average="binary", zero_division=0)
    ap = average_precision_score(y, s) if y.sum() else float("nan")
    return {"n": int(len(y)), "n_pos": int(y.sum()), "precision": round(pr, 4), "recall": round(rc, 4),
            "f1": round(f, 4), "pr_auc": round(ap, 4), "threshold": round(float(thr), 6)}


def fpr_by_site(df, s, thr):
    """사이트 종류별 오탐률: 음성(채점 대상) 중 문턱값 이상으로 잡힌 비율."""
    d = df.assign(_s=np.asarray(s, dtype=float))
    d = d[d["scored"] & (d["y"] == 0)]
    out = d.groupby("site_type")["_s"].agg(n="size", fp=lambda v: int((v >= thr).sum()))
    out["fpr"] = (out["fp"] / out["n"]).round(4)
    return out.reset_index()


# ---------- 출력 ----------
def write_pred(path, ids, scores, thr, model_id, config_hash, commit):
    """H7 형식 예측 파일. pred 는 검증셋에서 정한 문턱값으로 낸다."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    s = np.asarray(scores, dtype=float)
    pd.DataFrame({"image_id": list(ids), "score": np.round(s, 6), "pred": (s >= thr).astype(int),
                  "model_id": model_id, "config_hash": config_hash, "commit": commit})[PRED_COLS].to_csv(path, index=False)


def log_experiment(path, row):
    """실험 로그 CSV 에 한 줄 더한다. 없으면 머리줄부터 만든다."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    row = dict(row, date=time.strftime("%Y-%m-%d %H:%M"))
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LOG_COLS, extrasaction="ignore")
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in LOG_COLS})


def exp_id(model_id, seed):
    return f"{model_id}_s{seed}_{time.strftime('%m%d%H%M%S')}"


def save_json(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def data_args(ap):
    ap.add_argument("--split", required=True, help="split_v1.csv")
    ap.add_argument("--meta", nargs="+", required=True, help="meta.csv (여러 개 가능)")
    ap.add_argument("--ocr", nargs="+", required=True, help="ocr.csv (여러 개 가능)")
    ap.add_argument("--config", required=True)
    ap.add_argument("--out", default=str(HERE / "runs"))
    return ap
