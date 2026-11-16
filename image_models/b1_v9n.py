"""B1: OCR 글 + 1차 판정기 v9n 그대로 (학습 없음, 재계획 4절 「자명한 기준」).

이미지 한 장 = v9n 후보 줄 하나로 보고, 광고 점수 model.ad.score 에 조합형 자모 올림(conj_boost)까지 v9n 과 똑같이 매긴다.
v9n 규칙·가중치는 고치지 않는다. 숨김 기법 문턱값(HG·JAMO·TR·OF)은 이미지에 해당이 없어 쓰지 않는다.

pred 문턱값 두 가지를 함께 적는다.
  fixed : v9n 이 ETC(추가 유형)에 쓰는 광고 점수 0.5. 「v9n 그대로」의 기본
  val   : 검증셋 F1 최대 문턱값. B1+·M 계열과 같은 규칙으로 비교할 때 쓴다
예측 파일의 pred 는 설정의 threshold_mode 를 따른다.

사용:
  python b1_v9n.py --split split_v1.csv --meta meta.csv meta_hard.csv --ocr ocr.csv ocr_hard.csv --config configs/b1.yaml
준아 평가셋 추론(평가 이미지가 있는 쪽에서만):
  python b1_v9n.py ... --allow-test --score-only --thr <검증셋에서 정해 둔 값>
"""
import argparse
import pickle
import sys
from pathlib import Path

import numpy as np

import imgcommon as C

REPO = C.HERE.parent


def load_v9n(model_dir):
    sys.path[:0] = [str(REPO / "model2"), str(REPO / "model")]
    import rules4  # noqa: E402  (pickle 이 model2·model 모듈을 찾는다)
    m = pickle.load(open(Path(model_dir) / "model.pkl", "rb"))
    return m, rules4


def v9n_scores(texts, hrefs, model, rules4):
    rows = [{"sid": "img", "i": k, "parent": -1, "tag": "img", "text": t, "href": h, "f": {}, "lab": {}, "t_skip": 0}
            for k, (t, h) in enumerate(zip(texts, hrefs))]
    ad = model.ad.score(rows)
    if getattr(model, "conj_strong", False):
        ad = rules4.conj_boost(rows, ad, getattr(model, "conj_floor", 0.99))
    return np.asarray(ad, dtype=float)


def main():
    ap = C.data_args(argparse.ArgumentParser())
    ap.add_argument("--allow-test", action="store_true", help="평가셋 추론 전용(준아)")
    ap.add_argument("--score-only", action="store_true", help="문턱값을 새로 정하지 않고 --thr 로 pred 만 낸다")
    ap.add_argument("--thr", type=float, default=None)
    a = ap.parse_args()
    cfg, chash = C.load_config(a.config)
    commit = C.git_commit()
    mid = cfg["model_id"]
    out = Path(a.out) / mid
    df = C.load(a.split, a.meta, a.ocr, allow_test=a.allow_test)
    C.describe(df)

    model, rules4 = load_v9n(REPO / cfg["v9n_dir"])
    hrefs = df["link_href"] if cfg.get("use_href") and "link_href" in df else [""] * len(df)
    df["score"] = v9n_scores(df["text"].tolist(), list(hrefs), model, rules4)

    if a.score_only:
        if a.thr is None:
            raise SystemExit("--score-only 에는 --thr 가 필요하다")
        for s, g in df.groupby("split"):
            C.write_pred(out / f"pred_{mid}_{s}.csv", g["image_id"], g["score"], a.thr, mid, chash, commit)
        print(f"예측 파일: {out}")
        return

    val = df[(df["split"] == "val") & df["scored"]]
    thr = {"fixed": float(cfg.get("fixed_threshold", 0.5)), "val": C.best_threshold(val["y"], val["score"])}
    use = thr[cfg.get("threshold_mode", "fixed")]
    report = {"config_hash": chash, "commit": commit, "thresholds": thr, "threshold_mode": cfg.get("threshold_mode", "fixed")}
    for s in ("train", "val"):
        g = df[(df["split"] == s) & df["scored"]]
        if not len(g):
            continue
        for name, t in thr.items():
            m = C.metrics(g["y"], g["score"], t)
            report[f"{s}_{name}"] = m
            print(f"  {s} 문턱 {name}={t:.4f}: P {m['precision']} R {m['recall']} F1 {m['f1']} PR-AUC {m['pr_auc']}")
            if s == "val":
                C.log_experiment(out.parent / "experiments.csv", dict(m, exp_id=C.exp_id(mid, 0) + "_" + name, model_id=mid, config=a.config,
                                 config_hash=chash, seed=0, split=s, commit=commit, memo=f"threshold={name}"))
    fpr = C.fpr_by_site(df[df["split"] == "val"], df.loc[df["split"] == "val", "score"], use)
    out.mkdir(parents=True, exist_ok=True)
    fpr.to_csv(out / f"fpr_site_{mid}_val.csv", index=False)
    print(fpr.to_string(index=False))
    C.save_json(out / f"report_{mid}.json", report)
    for s, g in df.groupby("split"):
        C.write_pred(out / f"pred_{mid}_{s}.csv", g["image_id"], g["score"], use, mid, chash, commit)
    print(f"결과: {out}")


if __name__ == "__main__":
    main()
