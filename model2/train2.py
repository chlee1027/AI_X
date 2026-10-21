"""v2 모델: 기법은 규칙(rules.py), 학습은 「광고 문구인가」 하나. B 틀(8:2 + 5-fold)로 문턱과 보고 위치 방식을 고른다.

판정: 후보 요소마다 규칙이 낸 기법 t 에 대해, 광고 점수 >= 문턱[t] 이면 (요소, t) 를 낸다.
  같은 표본·같은 기법에서 조상과 자손이 함께 나오면 POLICY 로 하나만 남긴다:
    deep = 가장 안쪽(글자를 직접 담은 쪽), top = 가장 바깥(숨김이 시작된 쪽), prob = 광고 점수가 높은 쪽.
광고 점수: 문자 1~3gram TF-IDF(원문 + 복원문) -> 로지스틱 회귀. 라벨 = 요강 4종 정답 요소. 정답의 조상·자손과
  4종 정답이 없는 ETC·조합 양성 표본의 후보는 애매해서 학습에서 뺀다(v1 과 같음).
선택 기준: fold 1~5 의 fold 밖 예측 중 「같은 사이트가 다른 fold 에 없는 표본」에서의 점수
  ((45 x 재현율 + 35 x 정밀도) / 80). 10-17 시험 1회차에서 이 지표가 시험 점수에 가장 가까웠다.
  (v1 과 달리 사람이 개발 데이터 점수를 보고 규칙을 고칠 수 있다. 시험셋은 쓰지 않는다.)

사용: python train2.py --features ../model/cache/features.jsonl --splits ../dev_data/splits --out runs/v2
"""
import argparse
import csv
import json
import os
import pickle
import sys
import time
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "8")
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "model")]
import numpy as np  # noqa: E402
from scipy import sparse  # noqa: E402
from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402

from common import MAIN4  # noqa: E402
from textfeat import restore  # noqa: E402
from train import load_rows, score  # noqa: E402
from rules import techniques  # noqa: E402

SEED = 20261017
CS = (1.0, 4.0)
POLICIES = ("deep", "top", "prob")
THR_GRID = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95)


class AdModel:
    def __init__(self, C):
        self.C = C

    def _x(self, texts, fit):
        raw = [t.lower() for t in texts]
        res = [restore(t).lower() for t in texts]
        if fit:
            self.v1 = TfidfVectorizer(analyzer="char_wb", ngram_range=(1, 3), min_df=2, max_features=80000, sublinear_tf=True)
            self.v2 = TfidfVectorizer(analyzer="char_wb", ngram_range=(1, 3), min_df=2, max_features=80000, sublinear_tf=True)
            return sparse.hstack([self.v1.fit_transform(raw), self.v2.fit_transform(res)]).tocsr()
        return sparse.hstack([self.v1.transform(raw), self.v2.transform(res)]).tocsr()

    def fit(self, rows):
        use = [r for r in rows if not r["t_skip"]]
        y = np.array([int(any(r["lab"].values())) for r in use])
        self.lr = LogisticRegression(C=self.C, max_iter=3000, class_weight="balanced", random_state=SEED)
        self.lr.fit(self._x([r["text"] for r in use], True), y)
        return self

    def score(self, rows):
        return self.lr.predict_proba(self._x([r["text"] for r in rows], False))[:, 1]


import re  # noqa: E402
from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402

URL_RE = re.compile(r"https?://|www\.|\.(?:com|net|kr|io|xyz|top|shop|site|bet|vip|me|cc)\b", re.I)
HANDLE_RE = re.compile(r"@[A-Za-z0-9_]{3,}|텔레|텔레그램|카톡|카카오|라인|tg[:\s]|kakao|telegram", re.I)
PHONE_RE = re.compile(r"\d{2,4}[\s\-.=~·]*\d{3,4}[\s\-.=~·]*\d{4}")
TAGS2 = ("a", "span", "div", "p", "li", "font", "b", "strong", "td", "h1", "h2", "h3")


def side_feats(rows):
    """글자 언어와 무관한 광고 단서: 외부 절대주소 링크, URL·연락처·전화 꼴, 길이, 태그, 숨김 여부."""
    X = []
    for r in rows:
        t, h, f = r["text"], r.get("href") or "", r["f"]
        X.append([
            1.0 if h.startswith(("http://", "https://", "//")) else 0.0,
            1.0 if h and not h.startswith(("http", "//", "#", "javascript", "mailto", "tel")) else 0.0,
            1.0 if URL_RE.search(t) else 0.0, 1.0 if HANDLE_RE.search(t) else 0.0, 1.0 if PHONE_RE.search(t) else 0.0,
            np.log1p(len(t)), sum(ch.isdigit() for ch in t) / max(len(t), 1),
            float(f.get("nchild", 0)), float(f.get("depth", 0)), float(bool(r.get("rt"))),
        ] + [1.0 if r["tag"] == g else 0.0 for g in TAGS2])
    return np.asarray(X)


class AdModel2:
    """글자 점수(학습 안 3겹 OOF) + side_feats -> HistGradientBoosting."""

    def __init__(self, C):
        self.C = C

    def fit(self, rows):
        use = [r for r in rows if not r["t_skip"]]
        y = np.array([int(any(r["lab"].values())) for r in use])
        sids = sorted({r["sid"] for r in use})
        part = {s: k % 3 for k, s in enumerate(sids)}
        pk = np.array([part[r["sid"]] for r in use])
        oof = np.zeros(len(use))
        for k in range(3):
            tr = [r for r, p in zip(use, pk) if p != k]
            te = [r for r, p in zip(use, pk) if p == k]
            oof[pk == k] = AdModel(self.C).fit(tr).score(te)
        self.text = AdModel(self.C).fit(use)
        Z = np.hstack([oof[:, None], side_feats(use)])
        self.hgb = HistGradientBoostingClassifier(learning_rate=0.05, max_leaf_nodes=15, max_iter=300,
                                                  class_weight="balanced", random_state=SEED).fit(Z, y)
        return self

    def score(self, rows):
        Z = np.hstack([self.text.score(rows)[:, None], side_feats(rows)])
        return self.hgb.predict_proba(Z)[:, 1]


def lenient(det, gold, sids):
    """정답 표본 안의 같은 기법 추가 검출은 세지 않는다(데이터가 표본당 정답 요소를 하나만 표시해서)."""
    g = {(s, i, t) for s in sids for i, t in gold[s]}
    p = {x for x in det if x[0] in sids}
    tp = len(p & g)
    fp = sum(1 for s, i, t in p - g if not any(gt == t for _, gt in gold[s]))
    R, P = tp / max(len(g), 1), tp / max(tp + fp, 1)
    return {"score": (45 * R + 35 * P) / 80, "recall": R, "precision": P, "tp": tp, "fp": fp, "gold": len(g)}


class V2:
    """저장되는 최종 모델: 광고 모델 + 문턱 + 보고 위치 방식."""

    def __init__(self, ad, thr, policy):
        self.ad, self.thr, self.policy = ad, thr, policy

    def detect(self, rows, ad=None):
        """-> {(sid, i, t): (광고 점수, [근거])}"""
        if ad is None:
            ad = self.ad.score(rows)
        return decide(rows, ad, self.thr, self.policy)


def rule_cache(rows):
    for r in rows:
        if "rt" not in r:
            r["rt"] = techniques(r["f"], r["text"])


def decide(rows, ad, thr, policy):
    by = defaultdict(list)
    for k, r in enumerate(rows):
        for t, why in r["rt"].items():
            if ad[k] >= thr[t]:
                by[(r["sid"], t)].append((ad[k], r["f"].get("depth", 0), r["i"], why))
    par = {(r["sid"], r["i"]): r["parent"] for r in rows}

    def line(sid, x):
        s = set()
        while x >= 0:
            s.add(x)
            x = par.get((sid, x), -1)
        return s

    out = {}
    for (sid, t), lst in by.items():
        if policy == "deep":
            lst.sort(key=lambda z: (-z[1], -z[0]))
        elif policy == "top":
            lst.sort(key=lambda z: (z[1], -z[0]))
        else:
            lst.sort(key=lambda z: (-z[0], -z[1]))
        kept = []
        for p, d, i, why in lst:
            li = line(sid, i)
            if any(k in li or i in line(sid, k) for k in kept):
                continue
            kept.append(i)
            out[(sid, i, t)] = (float(p), why)
    return out


def pick(rows, ad, gold, sids):
    best = (-1, None, None)
    for pol in POLICIES:
        thr = {t: 0.5 for t in MAIN4}
        cur = lenient(set(decide(rows, ad, thr, pol)), gold, sids)["score"]
        for _ in range(3):
            for t in MAIN4:
                for v in THR_GRID:
                    trial = dict(thr, **{t: v})
                    s = lenient(set(decide(rows, ad, trial, pol)), gold, sids)["score"]
                    if s > cur + 1e-12:
                        cur, thr = s, trial
        if cur > best[0]:
            best = (cur, thr, pol)
    return best


def coverage(rows, gold):
    """규칙만으로 닿는 정답 비율(광고 판정이 완벽할 때의 재현율 상한)."""
    fired = {(r["sid"], r["i"], t) for r in rows for t in r["rt"]}
    g = {(s, i, t) for s in gold for i, t in gold[s]}
    per = {}
    for t in MAIN4:
        gt = {x for x in g if x[2] == t}
        per[t] = {"gold": len(gt), "rule_hit": len(gt & fired)}
    return {"gold": len(g), "rule_hit": len(g & fired), "per": per}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", required=True)
    ap.add_argument("--splits", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rows, gold, unresolved = load_rows(a.features)
    rule_cache(rows)
    fd = {r["id"]: int(r["fold"]) for r in csv.DictReader(open(Path(a.splits) / "folds_B.csv", encoding="utf-8"))}
    site = {r["id"]: r["site"] for r in csv.DictReader(open(Path(a.splits) / "pool.csv", encoding="utf-8"))}
    sids = sorted(s for s in gold if s in fd)
    sf = defaultdict(set)
    for s in sids:
        sf[site.get(s, "")].add(fd[s])
    evals = [s for s in sids if fd[s] > 0]
    clean = {s for s in evals if not (sf[site.get(s, "")] - {fd[s], 0})}
    by_sid = defaultdict(list)
    for k, r in enumerate(rows):
        by_sid[r["sid"]].append(k)
    log = {"seed": SEED, "unresolved_gold": unresolved, "coverage_all": coverage(rows, gold)}
    results = []
    KINDS = {"text": AdModel, "text+side": AdModel2}
    for kind, cls in KINDS.items():
        for C in CS:
            oof_rows, oof_ad = [], []
            for f in range(1, 6):
                tr = [rows[k] for s in sids if fd[s] != f for k in by_sid[s]]
                te = [rows[k] for s in sids if fd[s] == f for k in by_sid[s]]
                oof_rows += te
                oof_ad.append(cls(C).fit(tr).score(te))
            oof_ad = np.concatenate(oof_ad)
            s, thr, pol = pick(oof_rows, oof_ad, gold, clean)
            results.append((s, kind, C, thr, pol, oof_rows, oof_ad))
            print(f"{kind} C={C}: 같은 사이트 뺀 OOF(관대) {s:.4f} ({pol}, {thr})", flush=True)
    s, kind, C, thr, pol, oof_rows, oof_ad = max(results, key=lambda x: x[0])
    det = set(decide(oof_rows, oof_ad, thr, pol))
    log.update(chosen={"kind": kind, "C": C, "policy": pol, "thresholds": thr},
               oof_site_disjoint=score(det, gold, clean), oof_site_disjoint_lenient=lenient(det, gold, clean),
               n_site_disjoint=len(clean),
               oof_all=score(det, gold, set(evals)), oof_all_lenient=lenient(det, gold, set(evals)), n_oof=len(evals),
               coverage_site_disjoint=coverage([r for r in oof_rows if r["sid"] in clean], {k: gold[k] for k in clean}),
               all_configs=[{"kind": k, "C": c, "policy": p, "score": x} for x, k, c, _, p, *_ in results])
    final = V2(KINDS[kind](C).fit([rows[k] for s in sids for k in by_sid[s]]), thr, pol)
    with open(out / "model.pkl", "wb") as fh:
        pickle.dump(final, fh)
    log["seconds"] = round(time.time() - t0, 1)
    (out / "log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    sd = log["oof_site_disjoint_lenient"]
    print(f"끝: {kind} C={C} {pol} 같은 사이트 뺀 OOF(관대) {sd['score']:.4f} (재현 {sd['recall']:.3f} 정밀 {sd['precision']:.3f}), {log['seconds']}초")


if __name__ == "__main__":
    # 모델을 train2.V2 이름으로 저장되게(검사 스크립트에서 불러올 수 있게) 모듈로 다시 불러 실행한다
    import train2
    train2.main()
