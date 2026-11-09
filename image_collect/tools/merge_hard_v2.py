"""정연 2차 전달(11-08)을 명세 형식으로 맞춰 H2 묶음의 hard/ 에 넣는다. 정연 원본 파일은 바꾸지 않는다.

- set R_add -> R_hard, radd_ -> rhard_ (sha1 앞 16자리 그대로). 바뀐 id 는 id_map_add.csv
- 추가 50장 labeler 'Claude(v1기준 초안)' -> 'Claude초안+정연확인' (정연이 전부 확정했다고 알림)
- note 의 '임시 기준(11.7 확정 예정)' -> '임시 기준(11.8 확정)'
- 서민금융진흥원 새출발기금 안내 1장: v1 '공공기관 로고가 있어도 내용이 다른 공지면 normal' 에 따라 normal (labeler 채현)
- OCR: 기존 ocr_hard.csv 를 재사용하고 새 50장만 고정 엔진으로 읽음. lang 빈 칸은 OCR 문자 종류로 초안
- κ: label_b.csv 와 kappa.py 결과를 함께 넣음

사용: python tools/merge_hard_v2.py <정연 폴더> <출력 폴더>
"""
import csv
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pandas as pd  # noqa: E402

NEWSTART = "rhard_"  # 새출발기금 행은 note 로 찾는다


def guess(s):
    ko = bool(re.search("[가-힣]", s))
    la = bool(re.search("[A-Za-z]{2,}", s))
    return "mixed" if ko and la else "ko" if ko else "en" if la else "none"


def main():
    src, out = sys.argv[1:3]
    h = pd.read_csv(os.path.join(src, "meta_hard_초안.csv"), dtype=str).fillna("")
    add = h["set"] == "R_add"
    old_ids = h.loc[add, "image_id"].tolist()
    h.loc[add, "image_id"] = "rhard_" + h.loc[add, "sha1"].str[:16]
    ext = h["file"].str.rsplit(".", n=1).str[1].str.lower()
    new_file = "images/" + h["image_id"] + "." + ext
    os.makedirs(os.path.join(out, "images"), exist_ok=True)
    for a, b in zip(h["file"], new_file):
        shutil.copyfile(os.path.join(src, a), os.path.join(out, b))
    h["file"] = new_file
    pd.DataFrame({"image_id_old": old_ids, "image_id": h.loc[add, "image_id"]}).to_csv(
        os.path.join(out, "id_map_add.csv"), index=False, encoding="utf-8")
    h.loc[add, "set"] = "R_hard"
    h.loc[h["labeler"] == "Claude(v1기준 초안)", "labeler"] = "Claude초안+정연확인"
    h["note"] = h["note"].str.replace("임시 기준(11.7 확정 예정)", "임시 기준(11.8 확정)", regex=False)
    ns = h["note"].str.contains("새출발기금") & (h["label"] == "campaign")
    h.loc[ns, "label"] = "normal"
    h.loc[ns, "labeler"] = "채현"
    h.loc[ns, "note"] = "v1: 공공기관 정책 공지로 하지 말라는 내용이 아니어서 normal (채현 수정, 정연 원래 campaign) | " + h.loc[ns, "note"]
    print("새출발기금 수정", int(ns.sum()))

    old = pd.read_csv("deliver/for_junah/ocr_hard.csv", dtype=str).fillna("")
    old_boxes = {}
    with open("deliver/for_junah/ocr_boxes_hard.jsonl", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            old_boxes[r["image_id"]] = r["boxes"]
    keep = old[old["image_id"].isin(h["image_id"])]
    todo = h.loc[~h["image_id"].isin(keep["image_id"]), ["image_id", "file"]]
    print("OCR 재사용", len(keep), "새로", len(todo), flush=True)
    rows = keep.to_dict("records")
    boxes = {i: old_boxes[i] for i in keep["image_id"]}
    if len(todo):
        from ocr_engines import Paddle
        eng = Paddle()
        for k, r in enumerate(todo.itertuples()):
            x = eng.run(os.path.join(out, r.file))
            rows.append(dict(image_id=r.image_id, ocr_engine=eng.name, engine_version=eng.version, text=x["text"],
                             n_boxes=x["n_boxes"], conf_mean=x["conf_mean"]))
            boxes[r.image_id] = x["boxes"]
            if k % 10 == 0:
                print(k, flush=True)
    order = {i: n for n, i in enumerate(h["image_id"])}
    rows.sort(key=lambda r: order[r["image_id"]])
    with open(os.path.join(out, "ocr_hard.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["image_id", "ocr_engine", "engine_version", "text", "n_boxes", "conf_mean"])
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(out, "ocr_boxes_hard.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(dict(image_id=r["image_id"], boxes=boxes[r["image_id"]]), ensure_ascii=False) + "\n")

    text = {r["image_id"]: r["text"] for r in rows}
    blank = h["lang"] == ""
    h.loc[blank, "lang"] = h.loc[blank, "image_id"].map(text).fillna("").map(guess)
    print("lang OCR 초안", int(blank.sum()), h.loc[blank, "lang"].value_counts().to_dict())
    h.to_csv(os.path.join(out, "meta_hard.csv"), index=False, encoding="utf-8")
    print("meta_hard", len(h), h.groupby(["label", "unsure"]).size().to_dict(), h["labeler"].value_counts().to_dict())

    shutil.copyfile(os.path.join(src, "kappa", "label_b.csv"), os.path.join(out, "label_b.csv"))
    shutil.copyfile(os.path.join(src, "추가수집", "daeyeon_금감원조회결과.csv"), os.path.join(out, "대부중개_금감원조회결과.csv"))


if __name__ == "__main__":
    main()
