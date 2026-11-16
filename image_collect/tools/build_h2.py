"""H2 전달 묶음을 만든다. collect 원본은 건드리지 않는다.

1) meta: meta_초안.csv 에 채현 κ 라벨, 초안 점검 결과, 일괄 수정표를 합쳐 meta.csv 로
2) ocr_boxes.jsonl: 사용 목록만, file 을 image_id 로 바꿈
3) skipped.csv: 수집 샤드를 합침 (page_url, source_url, reason)
4) images: --images 를 주면 rimg_ 이름으로 복사 (약 1.2GB)

사용: python tools/build_h2.py --out deliver/h2 [--kappa κ.csv] [--check 점검.csv] [--images]
κ.csv: tools/kappa_xlsx.py export 결과. 점검.csv: tools/check_xlsx.py score 결과.
label 이 빈 행이 남아 있으면 경고만 하고 그대로 쓴다.
"""
import argparse
import glob
import json
import os
import re
import shutil

import pandas as pd

LABELS = {"illegal", "legal_ad", "campaign", "normal"}
SUBTYPES = {"gambling", "fake_doc", "adult", "sim_loan", "drug", "illegal_loan", "other"}


def apply_kappa(m, path):
    k = pd.read_csv(path, dtype=str).fillna("")
    missing = set(k["image_id"]) - set(m["image_id"])
    if missing:
        raise SystemExit(f"meta 에 없는 κ 행: {sorted(missing)[:5]}")
    blank = int((k["label"] == "").sum())
    if blank:
        print(f"[경고] κ 라벨 빈 칸 {blank}장")
    k = k[k["label"] != ""]
    bad = set(k["label"]) - LABELS
    if bad:
        raise SystemExit(f"잘못된 κ 라벨: {bad}")
    bad = set(k["subtype"]) - SUBTYPES - {""}
    if bad:
        raise SystemExit(f"잘못된 κ subtype: {bad}")
    k = k.set_index("image_id")
    rows = m["image_id"].isin(k.index)
    for c in ["label", "subtype", "unsure", "note"]:
        m.loc[rows, c] = m.loc[rows, "image_id"].map(k[c])
    m.loc[rows, "labeler"] = "채현"
    m.loc[rows & (m["label"] != "illegal"), "subtype"] = ""
    print("κ 반영", int(rows.sum()))
    return m


def apply_check(m, path):
    c = pd.read_csv(path, dtype=str).fillna("")
    wrong = c[c["verdict"] == "틀림"]
    if (wrong["correct"] == "").any():
        print("[경고] 틀림인데 맞는 라벨이 빈 행", wrong.loc[wrong["correct"] == "", "image_id"].tolist())
    rows = m["image_id"].isin(c.loc[c["verdict"] == "맞음", "image_id"])
    m.loc[rows, "labeler"] = "Claude초안+채현확인"
    for r in wrong[wrong["correct"] != ""].itertuples():
        i = m["image_id"] == r.image_id
        m.loc[i, "label"] = r.correct
        m.loc[i, "labeler"] = "채현"
        if r.correct != "illegal":
            m.loc[i, "subtype"] = ""
        if r.memo:
            m.loc[i, "note"] = r.memo
    unknown = c.loc[c["verdict"] == "모름", "image_id"]
    i = m["image_id"].isin(unknown)
    m.loc[i, "unsure"] = "1"
    m.loc[i & (m["note"] == ""), "note"] = "점검에서 판단 어려움"
    print("점검 맞음", int(rows.sum()), "틀림", len(wrong), "모름", len(unknown), "안 본 줄", int((c["verdict"] == "").sum()))
    return m


def fix_confirmed(m):
    """채현이 확인한 뒤 Claude 재판정에서 unsure 가 바뀐 행은 채현확인으로 적지 않는다."""
    old = pd.read_csv("collect/labels_draft.csv", dtype=str).fillna("")
    old["image_id"] = "rimg_" + old["file"].str.rsplit(".", n=1).str[0]
    was = m["image_id"].map(old.set_index("image_id")["unsure"]).fillna("")
    rows = (m["labeler"] == "Claude초안+채현확인") & (was != "") & (m["unsure"] != was)
    m.loc[rows, "labeler"] = "Claude초안"
    print("채현확인에서 Claude초안으로 고침", int(rows.sum()))
    return m


def fill_lang(m):
    """lang 빈 칸은 OCR 글의 문자 종류로 초안을 채운다. en 과 id 는 구분하지 못해 라틴 문자는 en 으로 둔다."""
    text = pd.read_csv("deliver/for_junah/ocr.csv", dtype=str).fillna("").set_index("image_id")["text"]

    def guess(s):
        ko = bool(re.search("[가-힣]", s))
        la = bool(re.search("[A-Za-z]{2,}", s))
        return "mixed" if ko and la else "ko" if ko else "en" if la else "none"

    rows = m["lang"] == ""
    m.loc[rows, "lang"] = m.loc[rows, "image_id"].map(text).fillna("").map(guess)
    print("lang OCR 초안", int(rows.sum()), m.loc[rows, "lang"].value_counts().to_dict())
    return m


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", default="deliver/for_junah/meta_초안.csv")
    ap.add_argument("--kappa", default="")
    ap.add_argument("--check", default="")
    ap.add_argument("--out", default="deliver/h2")
    ap.add_argument("--images", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)

    m = pd.read_csv(a.meta, dtype=str).fillna("")
    if a.kappa:
        m = apply_kappa(m, a.kappa)
    if a.check:
        m = apply_check(m, a.check)
    m = fix_confirmed(m)
    m = fill_lang(m)
    m["set"] = m["set"].where(m["label"] == "", (m["label"] == "illegal").map({True: "R_pos", False: "R_gen"}))
    if (m["label"] == "").any():
        print("[경고] 라벨 빈 행", int((m["label"] == "").sum()))
    no_note = int(((m["unsure"] == "1") & (m["note"] == "")).sum())
    if no_note:
        print("[경고] unsure=1 인데 note 없음", no_note)
    m.to_csv(os.path.join(a.out, "meta.csv"), index=False, encoding="utf-8")
    print("meta", len(m), m["label"].value_counts().to_dict(), m["labeler"].value_counts().to_dict())

    use = pd.read_csv("selection_v1/use_list.csv", dtype=str)["file"].tolist()
    ids = {f: "rimg_" + os.path.splitext(f)[0] for f in use}
    seen = set()
    with open(os.path.join(a.out, "ocr_boxes.jsonl"), "w", encoding="utf-8") as out:
        for p in sorted(glob.glob("collect/ocr_boxes*.jsonl")):
            with open(p, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    r = json.loads(line)
                    if r["file"] in ids and r["file"] not in seen:
                        seen.add(r["file"])
                        out.write(json.dumps(dict(image_id=ids[r["file"]], boxes=r["boxes"]), ensure_ascii=False) + "\n")
    print("ocr_boxes", len(seen), "없는 파일", len(set(use) - seen))

    frames = []
    for p in sorted(glob.glob("collect/skipped_*.csv")):
        try:
            frames.append(pd.read_csv(p, dtype=str))
        except pd.errors.EmptyDataError:
            pass
    sk = pd.concat(frames, ignore_index=True).fillna("").drop_duplicates()
    sk[["page_url", "source_url", "reason"]].to_csv(os.path.join(a.out, "skipped.csv"), index=False, encoding="utf-8")
    print("skipped", len(sk), sk["reason"].value_counts().to_dict())

    shutil.copyfile("kappa_v1/seed.txt", os.path.join(a.out, "seed.txt"))
    shutil.copyfile("kappa_v1/_order_private.csv", os.path.join(a.out, "kappa_order.csv"))
    scr = os.path.join(a.out, "scripts_fixed")
    shutil.rmtree(scr, ignore_errors=True)
    shutil.copytree("deliver/for_junah/scripts_fixed", scr, ignore=shutil.ignore_patterns("__pycache__"))
    print("seed.txt, kappa_order.csv, scripts_fixed 복사")

    if a.images:
        img = os.path.join(a.out, "images")
        os.makedirs(img, exist_ok=True)
        for f in use:
            shutil.copyfile(os.path.join("collect/images", f), os.path.join(img, ids[f] + os.path.splitext(f)[1].lower()))
        print("images", len(os.listdir(img)))


if __name__ == "__main__":
    main()
