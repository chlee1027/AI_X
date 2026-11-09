"""B1+ (1단계): OCR 글로 텍스트 분류기를 다시 학습한다. TF-IDF + 로지스틱 회귀 (재계획 4절 「표준 방법 (글)」).

v9n 글자 판정기와 같은 꼴(복원 글자 char_wb 1~3-gram)을 쓰되, 어휘와 가중치는 학습(train) 몫의 OCR 글로만 만든다.
C 는 설정의 후보 중 검증셋 PR-AUC 가 가장 큰 것을 고르고, 문턱값은 검증셋 F1 최대로 정한다.
로지스틱 회귀(lbfgs)는 시드에 따라 바뀌지 않으므로 한 번만 돌리고 로그에 그렇게 적는다.

M2 에 쓸 학습 몫 점수는 같은 모델이 자기 학습 데이터를 채점하면 부풀므로, group_id 단위 K겹 OOF 점수(oof_train)를 따로 낸다.

사용:
  python b1plus_tfidf.py --split split_v1.csv --meta meta.csv meta_hard.csv --ocr ocr.csv ocr_hard.csv --config configs/b1plus_tfidf.yaml
"""
import argparse
import pickle
import sys
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.model_selection import GroupKFold

import imgcommon as C

sys.path.insert(0, str(C.HERE.parent / "model"))
from textfeat import restore  # noqa: E402  v9n 과 같은 글자 복원(NFKC·보이지 않는 글자·닮은꼴·자모 조합)


def prep(texts):
    return [restore(t).lower() for t in texts]


def fit(texts, y, cfg, c):
    v = TfidfVectorizer(analyzer=cfg.get("analyzer", "char_wb"), ngram_range=tuple(cfg.get("ngram", [1, 3])),
                        min_df=cfg.get("min_df", 2), max_features=cfg.get("max_features", 80000), sublinear_tf=True)
    X = v.fit_transform(texts)
    lr = LogisticRegression(C=c, max_iter=3000, class_weight="balanced").fit(X, y)
    return v, lr


def score(model, texts):
    v, lr = model
    return lr.predict_proba(v.transform(texts))[:, 1]


def main():
    ap = C.data_args(argparse.ArgumentParser())
    ap.add_argument("--allow-test", action="store_true", help="평가셋 추론 전용(준아)")
    ap.add_argument("--infer-only", default=None, help="저장된 model_<id>.pkl 로 점수만 낸다(평가셋 추론)")
    a = ap.parse_args()
    cfg, chash = C.load_config(a.config)
    commit = C.git_commit()
    mid = cfg["model_id"]
    out = Path(a.out) / mid
    out.mkdir(parents=True, exist_ok=True)
    df = C.load(a.split, a.meta, a.ocr, allow_test=a.allow_test)
    C.describe(df)
    df["t"] = prep(df["text"])
    if a.infer_only:
        saved = pickle.load(open(a.infer_only, "rb"))
        s = score((saved["vectorizer"], saved["lr"]), df["t"])
        for sp in df["split"].unique():
            k = (df["split"] == sp).to_numpy()
            C.write_pred(out / f"pred_{mid}_{sp}.csv", df["image_id"][k], s[k], saved["threshold"], mid, saved["config_hash"], commit)
        print(f"결과: {out}")
        return
    tr = df[(df["split"] == "train") & df["scored"]]
    va = df[(df["split"] == "val") & df["scored"]]

    best = None
    for c in cfg["C_grid"]:
        m = fit(tr["t"], tr["y"], cfg, c)
        ap_ = average_precision_score(va["y"], score(m, va["t"]))
        print(f"  C={c}: val PR-AUC {ap_:.4f}")
        if best is None or ap_ > best[0]:
            best = (ap_, c, m)
    _, c, model = best
    df["score"] = score(model, df["t"])
    va_s = df.loc[va.index, "score"]
    thr = C.best_threshold(va["y"], va_s)
    report = {"config_hash": chash, "commit": commit, "C": c, "threshold": thr, "vocab": len(model[0].vocabulary_)}
    for s, g in (("train", tr), ("val", va)):
        m = C.metrics(g["y"], df.loc[g.index, "score"], thr)
        report[s] = m
        print(f"  {s}: P {m['precision']} R {m['recall']} F1 {m['f1']} PR-AUC {m['pr_auc']} (문턱 {thr:.4f})")
    C.log_experiment(out.parent / "experiments.csv", dict(report["val"], exp_id=C.exp_id(mid, 0), model_id=mid, config=a.config,
                     config_hash=chash, seed=0, split="val", commit=commit, memo=f"C={c}; lbfgs 결정적이라 시드 1회"))
    C.fpr_by_site(df[df["split"] == "val"], df.loc[df["split"] == "val", "score"], thr).to_csv(out / f"fpr_site_{mid}_val.csv", index=False)

    # M2 용 학습 몫 OOF 점수: group_id 로 K겹, 각 겹은 나머지 학습 몫으로만 어휘·가중치를 다시 만든다
    k = int(cfg.get("oof_folds", 5))
    trall = df[df["split"] == "train"]
    oof = np.zeros(len(trall))
    for f_tr, f_te in GroupKFold(n_splits=k).split(trall, groups=trall["group_id"]):
        fit_rows = trall.iloc[f_tr]
        fit_rows = fit_rows[fit_rows["scored"]]
        oof[f_te] = score(fit(fit_rows["t"], fit_rows["y"], cfg, c), trall["t"].iloc[f_te])
    sc = trall["scored"].to_numpy()
    report["train_oof"] = C.metrics(trall["y"][sc], oof[sc], thr)
    print(f"  train OOF({k}겹): PR-AUC {report['train_oof']['pr_auc']}")

    C.save_json(out / f"report_{mid}.json", report)
    with open(out / f"model_{mid}.pkl", "wb") as fh:
        pickle.dump({"vectorizer": model[0], "lr": model[1], "threshold": thr, "config_hash": chash}, fh)
    C.write_pred(out / f"pred_{mid}_val.csv", df.loc[df["split"] == "val", "image_id"], df.loc[df["split"] == "val", "score"],
                 thr, mid, chash, commit)
    C.write_pred(out / f"pred_{mid}_train_oof.csv", trall["image_id"], oof, thr, mid, chash, commit)
    print(f"결과: {out}")


if __name__ == "__main__":
    main()
