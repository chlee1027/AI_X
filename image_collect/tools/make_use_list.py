"""정상 이미지 사이트당 상한으로 사용 목록과 제외 목록을 만든다. 이미지 파일은 건드리지 않는다.

규칙 (라벨 초안 기준, 모델 결과는 쓰지 않음)
  유지: illegal, legal_ad, campaign 전부
  제외: 정연 R_hard 와 바이트가 같은 11장 (R_hard 쪽을 남긴다)
  상한: 나머지(other, 라벨 없음)는 첫 수집 기록의 사이트별로 시드 고정 무작위 CAP 장까지

사용: python tools/make_use_list.py [--cap 100] [--seed 20261106] [--out selection_v1]
"""
import argparse
import glob
import os

import numpy as np
import pandas as pd

SAME_AS_R_HARD = {
    "f2d3f0f83651b844.jpg", "4b70c53c1aa50aca.png", "aa42d4f201d02dc0.png", "7d9109e1f4a2f7b4.png",
    "f2b3def99a48f0c3.jpg", "ecc0bfd6d9c55e54.jpg", "76a0b4115bbd9672.gif", "6959e92aacc9da79.jpg",
    "eee2499bdc7a6d8d.jpg", "cb57717583209e05.png", "5a3125a04b75f580.png",
}
KEEP = {"illegal", "legal_ad", "campaign"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=int, default=100)
    ap.add_argument("--seed", type=int, default=20261106)
    ap.add_argument("--out", default="selection_v1")
    args = ap.parse_args()

    lab = pd.concat([pd.read_csv(f"collect/{x}.csv", dtype=str).fillna("")
                     for x in ["labels_draft", "labels_draft_add"]]).set_index("file")
    imgs = sorted(os.listdir("collect/images"))
    occ = pd.concat([pd.read_csv(f, dtype=str, usecols=["file", "site", "site_type"])
                     for f in sorted(glob.glob("collect/occurrences_*.csv"))]).fillna("")
    occ["file"] = occ["file"].map(os.path.basename)
    df = occ.drop_duplicates("file").set_index("file").reindex(imgs)
    df["label"] = [lab["label"].get(f, "") for f in imgs]

    df["reason"] = ""
    is_keep = df["label"].isin(KEEP)
    df.loc[is_keep, "reason"] = "keep_" + df.loc[is_keep, "label"]
    is_dup = df.index.isin(SAME_AS_R_HARD)
    df.loc[is_dup, "reason"] = "excluded_same_as_R_hard"

    rng = np.random.default_rng(args.seed)
    rest = df[df["reason"] == ""]
    for site in sorted(rest["site"].unique()):
        ids = rest.index[rest["site"] == site].to_numpy()
        pick = ids if len(ids) <= args.cap else rng.choice(ids, args.cap, replace=False)
        df.loc[ids, "reason"] = f"excluded_over_cap_{args.cap}"
        df.loc[pick, "reason"] = "sampled_normal_candidate"

    os.makedirs(args.out, exist_ok=True)
    out = df.reset_index()[["file", "site", "site_type", "reason"]]
    used = out[~out["reason"].str.startswith("excluded")]
    excl = out[out["reason"].str.startswith("excluded")]
    used.to_csv(f"{args.out}/use_list.csv", index=False, encoding="utf-8")
    excl.to_csv(f"{args.out}/excluded_list.csv", index=False, encoding="utf-8")
    print("사용", len(used), "제외", len(excl), "합계", len(out))


if __name__ == "__main__":
    main()
