"""라벨 초안과 수집 기록을 합쳐 전달용 meta.csv, ocr.csv, 점검 표본을 만든다. 이미지는 건드리지 않는다.

입력
  selection_v1/use_list.csv, collect/occurrences_*.csv, collect/ocr_raw*.csv, collect/labels_draft*.csv
  kappa_v1/_order_private.csv, kappa_v1/meta_nolabel_343.csv
  --results 폴더의 result_rj.csv, result_vw1~3.csv, set_rule.csv 는 --rule 로 받음
labeler
  채현(대기)              κ 표본. 채현이 직접 라벨을 달 칸이라 label 을 비운다
  Claude초안+채현확인     채현이 확인한 395장 중 재판정에서 라벨이 그대로인 것
  Claude초안              Claude 가 그림을 보고 단 것
  Claude규칙초안          그림을 보지 않고 규칙으로 normal 로 둔 것

사용: python tools/build_meta.py --results <폴더> --rule <set_rule.csv> --out deliver/for_junah
"""
import argparse
import glob
import hashlib
import os

import numpy as np
import pandas as pd

COLS = ["image_id", "set", "file", "sha1", "source_url", "page_url", "site", "site_type", "element", "w", "h",
        "render_w", "render_h", "x", "y", "selector", "link_href", "alt", "lang", "collected_at",
        "label", "subtype", "unsure", "note", "labeler", "phash", "sites_all"]
CAT2SUB = {"gambling": "gambling", "forgery": "fake_doc", "adult": "adult", "drug": "drug", "etc": "other", "invest": "other"}
LABELS = {"illegal", "legal_ad", "campaign", "normal"}
SUBTYPES = {"gambling", "fake_doc", "adult", "sim_loan", "drug", "illegal_loan", "other"}


def read_results(folder):
    frames = []
    for n in ["result_rj", "result_vw1", "result_vw2", "result_vw3"]:
        d = pd.read_csv(os.path.join(folder, n + ".csv"), dtype=str).fillna("")
        d["source"] = n
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--rule", required=True)
    ap.add_argument("--out", default="deliver/for_junah")
    ap.add_argument("--seed", type=int, default=20261109)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    use = pd.read_csv("selection_v1/use_list.csv", dtype=str).fillna("")
    conf = pd.read_csv("collect/labels_draft.csv", dtype=str).fillna("")
    add = pd.read_csv("collect/labels_draft_add.csv", dtype=str).fillna("")
    old = pd.concat([conf, add]).set_index("file")
    res = read_results(a.results)
    if res["file"].duplicated().any():
        print("[경고] 결과 중복 파일", int(res["file"].duplicated().sum()), "장, 뒤의 것을 쓴다")
        res = res.drop_duplicates("file", keep="last")
    res = res.set_index("file")
    if not set(res.index) <= set(use["file"]):
        raise SystemExit(f"사용 목록에 없는 파일: {sorted(set(res.index) - set(use['file']))[:5]}")
    bad = set(res["label"]) - LABELS - {""}
    if bad:
        raise SystemExit(f"잘못된 라벨: {bad}")
    bad = set(res["subtype"]) - SUBTYPES - {""}
    if bad:
        raise SystemExit(f"잘못된 subtype: {bad}")

    order = pd.read_csv("kappa_v1/_order_private.csv", dtype=str)
    small = set(pd.read_csv("kappa_v1/meta_nolabel_343.csv", dtype=str)["image_id"])
    kset = order.set_index("image_id")["set"]
    rule = set(pd.read_csv(a.rule, dtype=str)["file"])

    rows = []
    for f in use["file"]:
        iid = "rimg_" + os.path.splitext(f)[0]
        if iid in small:
            rows.append(dict(file=f, label="", subtype="", unsure="", note="", labeler="채현(대기)"))
        elif f in res.index:
            r = res.loc[f]
            same = f in set(conf["file"]) and r["label"].replace("normal", "other") == old.loc[f, "label"]
            rows.append(dict(file=f, label=r["label"], subtype=r["subtype"] if r["label"] == "illegal" else "",
                             unsure=r["unsure"] or "0", note=r["note"],
                             labeler="Claude초안+채현확인" if same else "Claude초안"))
        elif f in old.index:
            if old.loc[f, "label"] != "other":
                raise SystemExit(f"재판정 결과 없음: {f}")
            rows.append(dict(file=f, label="normal", subtype="", unsure="0", note="",
                             labeler="Claude초안+채현확인" if f in set(conf["file"]) else "Claude초안"))
        elif f in rule:
            rows.append(dict(file=f, label="normal", subtype="", unsure="0", note="", labeler="Claude규칙초안"))
        else:
            rows.append(dict(file=f, label="normal", subtype="", unsure="0", note="", labeler="Claude초안"))
    lab = pd.DataFrame(rows).set_index("file")

    occ = pd.concat([pd.read_csv(p, dtype=str) for p in sorted(glob.glob("collect/occurrences_*.csv"))]).fillna("")
    occ["file"] = occ["file"].map(os.path.basename)
    sites = occ.groupby("file")["site"].agg(lambda s: ";".join(sorted({x for x in s if x})))
    first = occ.drop_duplicates("file").set_index("file").reindex(use["file"])
    phash = pd.read_csv("deliver/phash_use.csv", dtype=str).set_index("file")["phash"]

    m = first.copy()
    m["sha1"] = [hashlib.sha1(open(os.path.join("collect/images", f), "rb").read()).hexdigest() for f in m.index]
    if not all(s.startswith(os.path.splitext(f)[0]) for s, f in zip(m["sha1"], m.index)):
        raise SystemExit("파일 이름과 SHA-1 이 다른 파일이 있다")
    m["image_id"] = ["rimg_" + os.path.splitext(f)[0] for f in m.index]
    m["file_old"] = m.index
    m["file"] = ["images/rimg_" + os.path.splitext(f)[0] + os.path.splitext(f)[1].lower() for f in m.index]
    for c in ["label", "subtype", "unsure", "note", "labeler"]:
        m[c] = lab[c]
    m["set"] = np.where(m["label"] == "illegal", "R_pos", "R_gen")
    m.loc[m["image_id"].isin(small), "set"] = m.loc[m["image_id"].isin(small), "image_id"].map(kset)
    m["lang"] = [old["lang"].get(f, "") for f in m["file_old"]]
    m["phash"] = phash.reindex(m["file_old"]).values
    m["sites_all"] = sites.reindex(m["file_old"]).values
    for c in COLS:
        if c not in m:
            m[c] = ""
    m[COLS].to_csv(os.path.join(a.out, "meta_초안.csv"), index=False, encoding="utf-8")

    ocr = pd.concat([pd.read_csv(p, dtype=str) for p in glob.glob("collect/ocr_raw*.csv")]).drop_duplicates("file").set_index("file")
    o = ocr.reindex(m["file_old"]).reset_index()
    o.insert(0, "image_id", m["image_id"].values)
    o[["image_id", "ocr_engine", "engine_version", "text", "n_boxes", "conf_mean"]].to_csv(os.path.join(a.out, "ocr.csv"), index=False, encoding="utf-8")

    # 점검 표본: 채현이 볼 불법 초안 100장, normal 초안 100장 (κ 표본과 겹치지 않음)
    rng = np.random.default_rng(a.seed)
    done = m[m["labeler"] != "채현(대기)"]
    a_ill = done[(done["label"] == "illegal") & (done["labeler"] == "Claude초안")].sort_values("image_id")
    a_nor = done[(done["label"] == "normal") & (done["unsure"] == "0")].sort_values("image_id")
    ci = a_ill.iloc[rng.choice(len(a_ill), min(100, len(a_ill)), replace=False)]
    cn = a_nor.iloc[rng.choice(len(a_nor), min(100, len(a_nor)), replace=False)]
    chk = pd.concat([ci, cn]).sample(frac=1, random_state=a.seed)
    chk[["image_id", "file_old", "label", "subtype", "unsure", "note", "labeler"]].to_csv(os.path.join(a.out, "..", "check_sample.csv"), index=False, encoding="utf-8")

    v = m[m["labeler"] != "채현(대기)"]
    print("행", len(m), "κ 대기", int((m["labeler"] == "채현(대기)").sum()))
    print("label", v["label"].value_counts().to_dict())
    print("illegal unsure", v[v["label"] == "illegal"]["unsure"].value_counts().to_dict())
    print("unsure=1 전체", int((v["unsure"] == "1").sum()))
    print("subtype", v[v["label"] == "illegal"]["subtype"].value_counts().to_dict())
    print("labeler", m["labeler"].value_counts().to_dict())
    print("임시 표시", v["note"].str.extract(r"(임시:\S+)")[0].value_counts().to_dict())
    print("삭제요청", int(v["note"].str.contains("삭제요청").sum()))
    print("빈 subtype illegal", int(((v["label"] == "illegal") & (v["subtype"] == "")).sum()))
    print("빈 note unsure=1", int(((v["unsure"] == "1") & (v["note"] == "")).sum()))
    print("OCR 행", len(o), "점검", len(chk))


if __name__ == "__main__":
    main()
