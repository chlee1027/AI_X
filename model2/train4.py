"""v4 학습 (10-17). v2(train2.py, 동결)에서 광고 판정기의 구조 특징 depth 하나만 뺀다. 나머지(규칙·라벨·고르는 방식)는 같다.

이유(진행보고서 7-8·7-9절): depth 는 개발 데이터에서는 표본 조각의 #root 부터, 실제 사이트 검사에서는 body 부터 센다.
  개발 데이터의 시험 fold 에서 depth 만 +3 밀어도 v2 관대 점수 0.678 -> 0.426(재현 0.749 -> 0.282)로 무너진다(exp_shift.py).
  팀원 사이트(진단용)에서 놓친 69개 중 62개가 「규칙은 켜졌는데 광고 점수가 문턱 아래」였던 것과 맞는다(diag_site.py).
  depth 를 바깥 겹 수와 무관한 특징(height·own·leaf)으로 바꾼 후보는 빼기만 한 것보다 낮았다(exp_shift2.py).
글자 규칙은 rules4(기본값 digit_fix·phone·hangul_like)를 쓴다(exp_rules4.py: 관대 0.628 -> 0.638, HG 재현 0.673 -> 0.737).
후보: text(글자만, AdModel) / text+side(depth 뺀 side_feats, AdModel4), C 1·4, 정책 deep·top·prob.
고르는 기준은 train2 와 같다: 같은 사이트 뺀 5-fold OOF 관대 점수. 팀원 사이트·시험셋은 쓰지 않는다.

사용: python train4.py --features ../model/cache/features.jsonl --splits ../dev_data/splits --out runs/v4
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
from sklearn.ensemble import HistGradientBoostingClassifier  # noqa: E402

import train2  # noqa: E402
import rules4  # noqa: E402
from train2 import AdModel, AdModel2, V2, SEED, CS, side_feats, pick, decide, lenient, coverage, rule_cache  # noqa: E402
from train import load_rows, score  # noqa: E402

DEPTH_COL = 8  # side_feats 의 depth 열


def side_feats4(rows):
    return np.delete(side_feats(rows), [DEPTH_COL], axis=1)


class AdModel4(AdModel2):
    """AdModel2 와 같고 side_feats 에서 depth 만 뺀다."""

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
        Z = np.hstack([oof[:, None], side_feats4(use)])
        self.hgb = HistGradientBoostingClassifier(learning_rate=0.05, max_leaf_nodes=15, max_iter=300,
                                                  class_weight="balanced", random_state=SEED).fit(Z, y)
        return self

    def score(self, rows):
        Z = np.hstack([self.text.score(rows)[:, None], side_feats4(rows)])
        return self.hgb.predict_proba(Z)[:, 1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--features", required=True)
    ap.add_argument("--splits", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rules4.use()  # v4 글자 규칙(rules4.OPTS 기본값: digit_fix·phone·hangul_like, exp_rules4.py 로 고름)
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
    log = {"seed": SEED, "unresolved_gold": unresolved, "coverage_all": coverage(rows, gold), "change": "v2 - depth feature, rules4", "rules4": dict(rules4.OPTS)}
    results = []
    KINDS = {"text": AdModel, "text+side-depth": AdModel4}
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
               all_configs=[{"kind": k, "C": c, "policy": p, "score": x} for x, k, c, _, p, *_ in results])
    final = V2(KINDS[kind](C).fit([rows[k] for s in sids for k in by_sid[s]]), thr, pol)
    with open(out / "model.pkl", "wb") as fh:
        pickle.dump(final, fh)
    log["seconds"] = round(time.time() - t0, 1)
    (out / "log.json").write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    sd, ss = log["oof_site_disjoint_lenient"], log["oof_site_disjoint"]
    print(f"끝: {kind} C={C} {pol} 같은 사이트 뺀 OOF 관대 {sd['score']:.4f} (재현 {sd['recall']:.3f} 정밀 {sd['precision']:.3f})"
          f" 엄격 {ss['score']:.4f}, {log['seconds']}초")


if __name__ == "__main__":
    # 모델이 train4.AdModel4 이름으로 저장되게 모듈로 다시 불러 실행한다
    import train4
    train4.main()
