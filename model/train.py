"""학습과 선택. --method A(6:2:2) 또는 B(8:2 + 5-fold) 하나만 돈다. 두 방법은 같은 코드·같은 후보 범위를 쓴다.

모델(두 단계)
  1) 광고 문구 점수 T: 후보 요소 글자(원문 + 복원문)의 문자 1~3gram TF-IDF -> 로지스틱 회귀.
     학습 라벨 = 요강 4종 정답 요소이면 1. 정답 요소의 조상·자손과, 4종 정답이 없는 ETC·조합 양성 표본의 후보는
     광고인지 아닌지 애매해서 T 학습에서 뺀다. 학습 안에서는 3겹 교차로 만든 점수(OOF)를 2단계에 넘긴다.
  2) 기법별 판정 4개: 화면 특징(render.py) + 글자 통계(textfeat.stats) + T 점수 -> HistGradientBoosting.
  출력: 기법별 문턱을 넘은 후보. 같은 표본·같은 기법에서 조상과 자손이 함께 넘으면 확률이 높은 쪽만 남긴다.
선택(코드가 자동으로, 사람이 끼어들지 않음)
  후보 설정 GRID 8개 중 점수가 가장 높은 것, 그리고 기법별 문턱.
  점수 = (45 x 재현율 + 35 x 정밀도) / 80, 단위는 (표본, 요소, 기법). 요강 적격평가의 개수·정확도 배점 비율을 따른 것이다.
  A: 학습 몫으로 학습 -> 검증 몫에서 선택. 최종 모델 = 학습 몫으로 학습한 것.
  B: fold 0 은 늘 학습. fold 1~5 를 하나씩 빼고 학습해 뺀 fold 를 예측(OOF) -> OOF 전체에서 선택.
     최종 모델 = 남은 80% 전체로 학습.
정답 위치가 발췌에서 풀리지 않는 정답(-1)은 채점에서 빼고 건수만 적는다. 풀렸지만 후보가 아닌 정답은 놓친 것으로 센다.

사용: python train.py --method A|B --features cache/features.jsonl --splits <splits 폴더> --out runs/A
"""
import argparse
import hashlib
import os
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "8")
import json
import pickle
import random
import sys
import time
from collections import defaultdict
from pathlib import Path

import csv
import numpy as np
from scipy import sparse
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from common import MAIN4
from textfeat import restore, stats

SEED = 20261017
GRID = [{"C": c, "lr": lr, "leaves": lv} for c in (1.0, 4.0) for lr in (0.05, 0.1) for lv in (15, 31)]
VIS = ["op", "dispNone", "visHid", "clip", "zeroOv", "scale", "indent", "off", "offDist", "fs", "colA", "fillA",
       "contrast", "bgImg", "cv", "w", "h", "depth", "nchild", "ownLen", "fullLen"]
TAGS = ["a", "span", "div", "p", "li", "td", "font", "b", "strong", "h1", "h2", "h3", "em", "u", "i", "ul", "section", "article"]


# ---------- 데이터 ----------
def load_rows(path):
    """features.jsonl -> 후보 행 목록과 표본별 정답."""
    rows, gold, unresolved = [], {}, defaultdict(int)
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        sid = r["id"]
        g = set()
        for (loc, tech), gi in zip(r["gold"], r["gold_idx"]):
            if gi < 0:
                unresolved[r["cat"]] += 1
            else:
                g.add((gi, tech))
        gold[sid] = g
        cand_idx = {c["i"] for c in r["cands"]}
        anc = {}
        par = {c["i"]: c["parent"] for c in r["cands"]}
        gold_el = {gi for gi, _ in g}
        near = set()
        for gi in gold_el:  # 정답 요소의 조상
            p = par.get(gi, -1)
            while p >= 0:
                near.add(p)
                p = par.get(p, -1)
        for c in r["cands"]:  # 정답 요소의 자손
            p = c["parent"]
            while p >= 0:
                if p in gold_el:
                    near.add(c["i"])
                    break
                p = par.get(p, -1)
        ambiguous_sample = r["cat"] in ("ETC", "COMBO") and not g
        for c in r["cands"]:
            lab = {t: int((c["i"], t) in g) for t in MAIN4}
            rows.append({"sid": sid, "cat": r["cat"], "i": c["i"], "parent": c["parent"], "tag": c["tag"],
                         "text": c["text"], "href": c.get("href", ""), "f": c["f"], "lab": lab,
                         "t_skip": int(c["i"] in near or ambiguous_sample)})
        gold[sid] = g
        for gi, t in g:
            if gi not in cand_idx:
                pass  # 후보가 아닌 정답: 채점에서 놓친 것으로 센다
    return rows, gold, dict(unresolved)


def dense(rows):
    X = []
    for r in rows:
        f = r["f"]
        v = [float(f.get(k, 0) or 0) for k in VIS]
        v += [1.0 if r["tag"] == t else 0.0 for t in TAGS]
        v += [1.0 if r["href"] and not r["href"].startswith("#") else 0.0]
        v += stats(r["text"])
        X.append(v)
    return np.asarray(X, dtype=np.float64)


# ---------- 모델 ----------
class Model:
    def __init__(self, cfg):
        self.cfg = cfg

    def _tfidf(self, texts, fit):
        raw = [t.lower() for t in texts]
        res = [restore(t).lower() for t in texts]
        if fit:
            self.v1 = TfidfVectorizer(analyzer="char_wb", ngram_range=(1, 3), min_df=2, max_features=60000, sublinear_tf=True)
            self.v2 = TfidfVectorizer(analyzer="char_wb", ngram_range=(1, 3), min_df=2, max_features=60000, sublinear_tf=True)
            return sparse.hstack([self.v1.fit_transform(raw), self.v2.fit_transform(res)]).tocsr()
        return sparse.hstack([self.v1.transform(raw), self.v2.transform(res)]).tocsr()

    def _t_label(self, rows):
        return np.array([int(any(r["lab"].values())) for r in rows])

    def fit(self, rows, D):
        cfg = self.cfg
        y_ad = self._t_label(rows)
        use = np.array([not r["t_skip"] for r in rows])
        # 1) T 의 학습 안 OOF 점수(표본 단위 3겹)
        sids = sorted({r["sid"] for r in rows})
        rnd = random.Random(SEED)
        rnd.shuffle(sids)
        part = {s: k % 3 for k, s in enumerate(sids)}
        pk = np.array([part[r["sid"]] for r in rows])
        t_oof = np.zeros(len(rows))
        texts = [r["text"] for r in rows]
        for k in range(3):
            tr = (pk != k) & use
            te = pk == k
            m = Model(cfg)
            Xtr = m._tfidf([texts[i] for i in np.where(tr)[0]], True)
            if len(set(y_ad[tr])) < 2:
                continue
            lr = LogisticRegression(C=cfg["C"], max_iter=2000, class_weight="balanced", random_state=SEED)
            lr.fit(Xtr, y_ad[tr])
            t_oof[te] = lr.predict_proba(m._tfidf([texts[i] for i in np.where(te)[0]], False))[:, 1]
        # 최종 T
        Xall = self._tfidf([texts[i] for i in np.where(use)[0]], True)
        self.t = LogisticRegression(C=cfg["C"], max_iter=2000, class_weight="balanced", random_state=SEED)
        self.t.fit(Xall, y_ad[use])
        # 2) 기법별 판정
        Z = np.hstack([D, t_oof[:, None]])
        self.clf = {}
        for t in MAIN4:
            y = np.array([r["lab"][t] for r in rows])
            if y.sum() == 0:
                self.clf[t] = None
                continue
            c = HistGradientBoostingClassifier(learning_rate=cfg["lr"], max_leaf_nodes=cfg["leaves"], max_iter=300,
                                               class_weight="balanced", random_state=SEED)
            c.fit(Z, y)
            self.clf[t] = c
        return self

    def predict(self, rows, D):
        ts = self.t.predict_proba(self._tfidf([r["text"] for r in rows], False))[:, 1]
        Z = np.hstack([D, ts[:, None]])
        return {t: (self.clf[t].predict_proba(Z)[:, 1] if self.clf[t] is not None else np.zeros(len(rows))) for t in MAIN4}


# ---------- 채점 ----------
def decide(rows, prob, thr):
    """문턱을 넘은 (표본, 요소, 기법). 같은 표본·기법에서 조상-자손이 같이 넘으면 확률 높은 쪽만."""
    by = defaultdict(list)
    for k, r in enumerate(rows):
        for t in MAIN4:
            if prob[t][k] >= thr[t]:
                by[(r["sid"], t)].append((prob[t][k], r["i"], r["parent"]))
    par = {(r["sid"], r["i"]): r["parent"] for r in rows}
    out = set()
    for (sid, t), lst in by.items():
        kept = []
        for p, i, _ in sorted(lst, reverse=True):
            def line(x):
                s = set()
                while x >= 0:
                    s.add(x)
                    x = par.get((sid, x), -1)
                return s
            li = line(i)
            if any(k in li or i in line(k) for k in kept):
                continue
            kept.append(i)
            out.add((sid, i, t))
    return out


def score(pred, gold, sids):
    g = {(s, i, t) for s in sids for i, t in gold[s]}
    p = {x for x in pred if x[0] in sids}
    tp = len(p & g)
    rec = tp / len(g) if g else 0.0
    pre = tp / len(p) if p else 0.0
    per = {}
    for t in MAIN4:
        gt = {x for x in g if x[2] == t}
        pt = {x for x in p if x[2] == t}
        tpt = len(pt & gt)
        per[t] = {"gold": len(gt), "pred": len(pt), "tp": tpt,
                  "recall": tpt / len(gt) if gt else None, "precision": tpt / len(pt) if pt else None}
    return {"score": (45 * rec + 35 * pre) / 80, "recall": rec, "precision": pre, "tp": tp, "gold": len(g),
            "pred": len(p), "per": per}


def pick_thresholds(rows, prob, gold, sids):
    thr = {t: 0.5 for t in MAIN4}
    grid = [0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.98]
    best = score(decide(rows, prob, thr), gold, sids)["score"]
    for _ in range(3):
        for t in MAIN4:
            for v in grid:
                trial = dict(thr, **{t: v})
                s = score(decide(rows, prob, trial), gold, sids)["score"]
                if s > best + 1e-12:
                    best, thr = s, trial
    return thr, best


# ---------- 실행 ----------
def code_hash():
    h = hashlib.sha256()
    here = Path(__file__).resolve().parent
    for n in ("common.py", "render.py", "textfeat.py", "train.py"):
        h.update((here / n).read_bytes())
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", choices=["A", "B"], required=True)
    ap.add_argument("--features", required=True)
    ap.add_argument("--splits", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rows, gold, unresolved = load_rows(a.features)
    D = dense(rows)
    sid_rows = defaultdict(list)
    for k, r in enumerate(rows):
        sid_rows[r["sid"]].append(k)

    def sub(sids):
        idx = [k for s in sids for k in sid_rows.get(s, [])]
        return [rows[k] for k in idx], D[idx]

    log = {"method": a.method, "code_sha256": code_hash(), "seed": SEED, "grid": GRID, "unresolved_gold": unresolved}
    if a.method == "A":
        sp = {r["id"]: r["split"] for r in csv.DictReader(open(Path(a.splits) / "split_A.csv", encoding="utf-8"))}
        tr = sorted(s for s in gold if sp.get(s) == "train")
        va = sorted(s for s in gold if sp.get(s) == "valid")
        Rtr, Dtr = sub(tr)
        Rva, Dva = sub(va)
        results = []
        for cfg in GRID:
            m = Model(cfg).fit(Rtr, Dtr)
            prob = m.predict(Rva, Dva)
            thr, s = pick_thresholds(Rva, prob, gold, set(va))
            results.append((s, cfg, thr, m, prob))
            print(f"[A] {cfg} -> {s:.4f}", flush=True)
        s, cfg, thr, final, prob = max(results, key=lambda x: x[0])
        sel = score(decide(Rva, prob, thr), gold, set(va))
        log.update(n_train=len(tr), n_valid=len(va), chosen=cfg, thresholds=thr, selection_set="A valid",
                   selection_score=sel, all_configs=[{"cfg": c, "score": x} for x, c, *_ in results])
    else:
        fd = {r["id"]: int(r["fold"]) for r in csv.DictReader(open(Path(a.splits) / "folds_B.csv", encoding="utf-8"))}
        allsids = sorted(s for s in gold if s in fd)
        evals = sorted(s for s in allsids if fd[s] > 0)
        results = []
        for cfg in GRID:
            oof_rows, oof_prob = [], {t: [] for t in MAIN4}
            for f in range(1, 6):
                tr = [s for s in allsids if fd[s] != f]
                te = [s for s in allsids if fd[s] == f]
                Rtr, Dtr = sub(tr)
                Rte, Dte = sub(te)
                p = Model(cfg).fit(Rtr, Dtr).predict(Rte, Dte)
                oof_rows += Rte
                for t in MAIN4:
                    oof_prob[t].append(p[t])
            oof_prob = {t: np.concatenate(v) for t, v in oof_prob.items()}
            thr, s = pick_thresholds(oof_rows, oof_prob, gold, set(evals))
            results.append((s, cfg, thr, oof_rows, oof_prob))
            print(f"[B] {cfg} -> {s:.4f}", flush=True)
        s, cfg, thr, oof_rows, oof_prob = max(results, key=lambda x: x[0])
        sel = score(decide(oof_rows, oof_prob, thr), gold, set(evals))
        Rall, Dall = sub(allsids)
        final = Model(cfg).fit(Rall, Dall)
        log.update(n_train=len(allsids), n_oof=len(evals), chosen=cfg, thresholds=thr, selection_set="B OOF fold1-5",
                   selection_score=sel, all_configs=[{"cfg": c, "score": x} for x, c, *_ in results])
        # 같은 사이트가 다른 fold 에도 있는 표본을 뺀 OOF 점수(교차검증이 사이트를 외운 몫을 보려고)
        pool = Path(a.splits) / "pool.csv"
        site = {r["id"]: r["site"] for r in csv.DictReader(open(pool, encoding="utf-8"))} if pool.exists() else {}
        sf = defaultdict(set)
        for sid in allsids:
            sf[site.get(sid, "")].add(fd[sid])
        clean = {s for s in evals if not (sf[site.get(s, "")] - {fd[s], 0})}
        log["selection_score_site_disjoint"] = score(decide(oof_rows, oof_prob, thr), gold, clean)
        log["n_site_disjoint"] = len(clean)
    with open(out / "model.pkl", "wb") as f:
        pickle.dump({"model": final, "thresholds": thr, "cfg": cfg, "code_sha256": log["code_sha256"]}, f)
    log["seconds"] = round(time.time() - t0, 1)
    (out / "log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{a.method}] 끝: 선택 {cfg}, 점수 {log['selection_score']['score']:.4f}, {log['seconds']}초")


if __name__ == "__main__":
    # 모델을 train.Model 이름으로 저장되게(score_test.py 에서 불러올 수 있게) 모듈로 다시 불러 실행한다
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import train
    train.main()
