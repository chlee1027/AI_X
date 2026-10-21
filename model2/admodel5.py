"""v5 광고 판정기와 학습용 음성 데이터 (10-17). eval_sites.py 에서 비교한 것과 같은 코드를 학습·검사가 함께 쓰게 모은 것.

AdSel : 글자 점수(학습 안 3겹 OOF) + 고른 side_feats 열 -> HistGradientBoosting. cols=None 이면 글자 점수만.
neg_rows : 광고 없는 공공기관 사이트(sites/N_*, 개발 표본 출처에 없는 기관)의 후보를 음성으로.
  규칙이 켜진 후보만(판정기가 판단하는 대상), 사이트 안에서 (글자, 태그, 링크 꼴, 켜진 기법)이 같은 것은 하나만(메뉴가 페이지마다 반복),
  사이트마다 cap 개까지(한 기관이 학습을 지배하지 않게). 근거: 진행보고서 7-10절.
"""
import json
import random
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier

from train2 import AdModel, SEED, side_feats, rule_cache

HERE = Path(__file__).resolve().parent
# side_feats 열: 0 외부 링크, 1 상대 링크, 2 URL 꼴, 3 메신저, 4 전화, 5 길이, 6 숫자 비율, 7 nchild, 8 depth, 9 규칙 발화, 10~21 태그
COLS = {"v4(구조 전부-깊이)": [c for c in range(22) if c != 8],
        "글자만": None,
        "글자+내용 단서": [0, 1, 2, 3, 4, 5, 6],
        "글자+내용 단서+태그": [0, 1, 2, 3, 4, 5, 6] + list(range(10, 22))}


class AdSel(AdModel):
    def __init__(self, C, cols):
        super().__init__(C)
        self.cols = cols

    def fit(self, rs):
        if self.cols is None:
            return super().fit(rs)
        use = [r for r in rs if not r["t_skip"]]
        y = np.array([int(any(r["lab"].values())) for r in use])
        ss = sorted({r["sid"] for r in use})
        part = {s: k % 3 for k, s in enumerate(ss)}
        pk = np.array([part[r["sid"]] for r in use])
        oof = np.zeros(len(use))
        for k in range(3):
            oof[pk == k] = AdModel(self.C).fit([r for r, p in zip(use, pk) if p != k]).score([r for r, p in zip(use, pk) if p == k])
        self.text = AdModel(self.C).fit(use)
        self.hgb = HistGradientBoostingClassifier(learning_rate=0.05, max_leaf_nodes=15, max_iter=300, class_weight="balanced",
                                                  random_state=SEED).fit(np.hstack([oof[:, None], side_feats(use)[:, self.cols]]), y)
        return self

    def score(self, rs):
        if self.cols is None:
            return super().score(rs)
        return self.hgb.predict_proba(np.hstack([self.text.score(rs)[:, None], side_feats(rs)[:, self.cols]]))[:, 1]


def load_site(d):
    rs = [json.loads(x) for x in open(Path(d) / "rows.jsonl", encoding="utf-8")]
    for r in rs:
        r.update(cat="", lab={}, t_skip=0)
    rule_cache(rs)
    return rs


def neg_rows(cap, seed=SEED, prefix="N_"):
    out = []
    for p in sorted((HERE / "sites").glob(prefix + "*")):
        if not (p / "rows.jsonl").exists():
            continue
        seen, keep = set(), []
        for r in load_site(p):
            if not r["rt"]:
                continue
            k = (r["text"], r["tag"], (r.get("href") or "")[:4], tuple(sorted(r["rt"])))
            if k in seen:
                continue
            seen.add(k)
            keep.append(r)
        random.Random(seed).shuffle(keep)
        for r in keep[:cap]:
            r["sid"] = p.name + "|" + r["sid"]
        out += keep[:cap]
    return out
