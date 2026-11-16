"""B1+ (2단계): KLUE-RoBERTa 미세조정 + H6 글 임베딩 추출. Colab L4 에서 돌린다.

- 학습 몫(unsure=0)으로 미세조정, 에폭 수는 설정에 고정, 문턱값은 검증셋 F1 최대. 시드 3회(설정 seeds)를 돌려 평균 ± 표준편차를 로그에 남긴다.
- H6 임베딩(다영 M2 용)은 첫 시드에서 만든다. 마지막 층 평균 풀링 벡터(768차원, float16).
  학습 몫 임베딩은 자기 학습 데이터를 본 모델에서 뽑으면 M2 가 부푼 신호를 배우므로, group_id 단위 K겹으로 다시 미세조정해
  각 겹이 보지 않은 몫에서 뽑는다(OOF). 검증 몫은 학습 몫 전체로 학습한 모델에서 뽑는다. 평가 몫은 준아가 같은 모델로 뽑는다.

사용:
  python b1plus_klue.py --split split_v1.csv --meta meta.csv meta_hard.csv --ocr ocr.csv ocr_hard.csv --config configs/b1plus_klue.yaml
준아 평가셋 임베딩·점수(평가 이미지가 있는 쪽에서만):
  python b1plus_klue.py ... --allow-test --infer-only runs/b1plus_klue/ckpt_s0 --thr <검증셋 문턱>
"""
import argparse
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import GroupKFold
from torch.utils.data import DataLoader
from transformers import AutoModelForSequenceClassification, AutoTokenizer, get_linear_schedule_with_warmup

import imgcommon as C


def set_seed(s):
    random.seed(s)
    np.random.seed(s)
    torch.manual_seed(s)
    torch.cuda.manual_seed_all(s)


def device():
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def batches(tok, texts, labels, cfg, shuffle, seed=0):
    enc = tok(list(texts), truncation=True, max_length=cfg["max_len"], padding=False)
    items = [{"input_ids": enc["input_ids"][k], "attention_mask": enc["attention_mask"][k], "labels": int(labels[k])}
             for k in range(len(texts))]

    def collate(b):
        out = tok.pad([{k: v for k, v in x.items() if k != "labels"} for x in b], return_tensors="pt")
        out["labels"] = torch.tensor([x["labels"] for x in b])
        return out

    g = torch.Generator().manual_seed(seed)
    return DataLoader(items, batch_size=cfg["batch_size"], shuffle=shuffle, collate_fn=collate, generator=g)


def train(cfg, texts, y, seed):
    set_seed(seed)
    tok = AutoTokenizer.from_pretrained(cfg["pretrained"])
    model = AutoModelForSequenceClassification.from_pretrained(cfg["pretrained"], num_labels=2).to(device())
    dl = batches(tok, texts, y, cfg, shuffle=True, seed=seed)
    opt = torch.optim.AdamW(model.parameters(), lr=float(cfg["lr"]), weight_decay=float(cfg.get("weight_decay", 0.01)))
    steps = len(dl) * cfg["epochs"]
    sch = get_linear_schedule_with_warmup(opt, int(steps * cfg.get("warmup", 0.1)), steps)
    pos = max(int(np.sum(y)), 1)
    w = torch.tensor([1.0, (len(y) - pos) / pos if cfg.get("class_weight") == "balanced" else 1.0], device=device())
    lossf = torch.nn.CrossEntropyLoss(weight=w)
    use_amp = device().type == "cuda"
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
    model.train()
    for ep in range(cfg["epochs"]):
        tot = 0.0
        for b in dl:
            b = {k: v.to(device()) for k, v in b.items()}
            lab = b.pop("labels")
            with torch.autocast(device_type=device().type, dtype=torch.float16, enabled=use_amp):
                loss = lossf(model(**b).logits, lab)
            opt.zero_grad()
            scaler.scale(loss).backward()
            scaler.step(opt)
            scaler.update()
            sch.step()
            tot += loss.item()
        print(f"    seed {seed} epoch {ep + 1}/{cfg['epochs']} loss {tot / max(len(dl), 1):.4f}", flush=True)
    return tok, model


@torch.no_grad()
def infer(tok, model, texts, cfg):
    """(양성 확률, 평균 풀링 임베딩) 을 돌려준다."""
    model.eval()
    dl = batches(tok, texts, np.zeros(len(texts)), cfg, shuffle=False)
    ps, es = [], []
    for b in dl:
        b = {k: v.to(device()) for k, v in b.items() if k != "labels"}
        out = model(**b, output_hidden_states=True)
        ps.append(torch.softmax(out.logits.float(), -1)[:, 1].cpu().numpy())
        h, m = out.hidden_states[-1].float(), b["attention_mask"].unsqueeze(-1).float()
        es.append(((h * m).sum(1) / m.sum(1).clamp(min=1)).cpu().numpy())
    return np.concatenate(ps), np.concatenate(es).astype(np.float16)


def save_emb(path, ids, emb):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    np.save(path, emb)
    pd.DataFrame({"image_id": list(ids), "row": range(len(ids))}).to_csv(str(path).replace(".npy", "_ids.csv"), index=False)


def main():
    ap = C.data_args(argparse.ArgumentParser())
    ap.add_argument("--allow-test", action="store_true")
    ap.add_argument("--infer-only", default=None, help="저장된 체크포인트로 점수·임베딩만 낸다(평가셋 추론)")
    ap.add_argument("--thr", type=float, default=None)
    ap.add_argument("--no-oof", action="store_true", help="OOF 임베딩을 건너뛴다(시험용)")
    a = ap.parse_args()
    cfg, chash = C.load_config(a.config)
    commit = C.git_commit()
    mid = cfg["model_id"]
    out = Path(a.out) / mid
    df = C.load(a.split, a.meta, a.ocr, allow_test=a.allow_test)
    C.describe(df)

    if a.infer_only:
        tok = AutoTokenizer.from_pretrained(a.infer_only)
        model = AutoModelForSequenceClassification.from_pretrained(a.infer_only).to(device())
        p, e = infer(tok, model, df["text"].tolist(), cfg)
        for s in df["split"].unique():
            k = (df["split"] == s).to_numpy()
            C.write_pred(out / f"pred_{mid}_{s}.csv", df["image_id"][k], p[k], a.thr if a.thr is not None else 0.5, mid, chash, commit)
            save_emb(out / f"emb_{mid}_{s}.npy", df["image_id"][k], e[k])
        print(f"결과: {out}")
        return

    tr = df[(df["split"] == "train") & df["scored"]]
    va = df[(df["split"] == "val") & df["scored"]]
    va_all = df[df["split"] == "val"]
    rows = []
    for i, seed in enumerate(cfg["seeds"]):
        tok, model = train(cfg, tr["text"].tolist(), tr["y"].to_numpy(), seed)
        p_all, e_all = infer(tok, model, va_all["text"].tolist(), cfg)
        p_va = pd.Series(p_all, index=va_all.index).loc[va.index]
        thr = C.best_threshold(va["y"], p_va)
        m = C.metrics(va["y"], p_va, thr)
        rows.append(m)
        print(f"  seed {seed}: val P {m['precision']} R {m['recall']} F1 {m['f1']} PR-AUC {m['pr_auc']} (문턱 {thr:.4f})")
        C.log_experiment(out.parent / "experiments.csv", dict(m, exp_id=C.exp_id(mid, seed), model_id=mid, config=a.config,
                         config_hash=chash, seed=seed, split="val", commit=commit))
        C.write_pred(out / f"pred_{mid}_val_s{seed}.csv", va_all["image_id"], p_all, thr, mid, chash, commit)
        C.fpr_by_site(va_all, p_all, thr).to_csv(out / f"fpr_site_{mid}_val_s{seed}.csv", index=False)
        if i == 0:
            ck = out / f"ckpt_s{seed}"
            model.save_pretrained(ck)
            tok.save_pretrained(ck)
            save_emb(out / f"emb_{mid}_val.npy", va_all["image_id"], e_all)
        del model
        torch.cuda.empty_cache()
    summ = {k: (round(float(np.mean([r[k] for r in rows])), 4), round(float(np.std([r[k] for r in rows])), 4))
            for k in ("precision", "recall", "f1", "pr_auc")}
    print("  시드 평균 ± 표준편차:", summ)

    if not a.no_oof:
        k = int(cfg.get("oof_folds", 5))
        trall = df[df["split"] == "train"]
        emb = np.zeros((len(trall), 0), dtype=np.float16)
        oof_p = np.zeros(len(trall))
        for f, (f_tr, f_te) in enumerate(GroupKFold(n_splits=k).split(trall, groups=trall["group_id"])):
            fit_rows = trall.iloc[f_tr]
            fit_rows = fit_rows[fit_rows["scored"]]
            print(f"  OOF {f + 1}/{k}: 학습 {len(fit_rows)}장, 추출 {len(f_te)}장", flush=True)
            tok, model = train(cfg, fit_rows["text"].tolist(), fit_rows["y"].to_numpy(), cfg["seeds"][0])
            p, e = infer(tok, model, trall["text"].iloc[f_te].tolist(), cfg)
            if emb.shape[1] == 0:
                emb = np.zeros((len(trall), e.shape[1]), dtype=np.float16)
            emb[f_te], oof_p[f_te] = e, p
            del model
            torch.cuda.empty_cache()
        save_emb(out / f"emb_{mid}_train_oof.npy", trall["image_id"], emb)
        C.write_pred(out / f"pred_{mid}_train_oof.csv", trall["image_id"], oof_p, 0.5, mid, chash, commit)
    C.save_json(out / f"report_{mid}.json", {"config_hash": chash, "commit": commit, "val_by_seed": rows, "val_mean_std": summ})
    print(f"결과: {out}")


if __name__ == "__main__":
    main()
