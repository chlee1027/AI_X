"""정연 R_hard 이미지를 고정 OCR 엔진(ocr_select/OCR_FIXED.txt)으로 읽어 명세 6절 형식으로 저장한다.

사용: python tools/ocr_hard.py <meta_hard 초안.csv> <id_map.csv> <원본 meta.csv> <collected 폴더의 부모> <출력 폴더>
출력: ocr_hard.csv (image_id, ocr_engine, engine_version, text, n_boxes, conf_mean), ocr_boxes_hard.jsonl (image_id, boxes)
"""
import csv
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pandas as pd  # noqa: E402
from ocr_engines import Paddle  # noqa: E402


def main():
    hard_path, map_path, orig_path, root, out = sys.argv[1:6]
    hard = pd.read_csv(hard_path, dtype=str).fillna("").set_index("image_id")
    idm = pd.read_csv(map_path, dtype=str)
    orig = pd.read_csv(orig_path, dtype=str, encoding="utf-8-sig").fillna("").set_index("image_id")
    eng = Paddle()
    os.makedirs(out, exist_ok=True)
    cols = ["image_id", "ocr_engine", "engine_version", "text", "n_boxes", "conf_mean"]
    fails = 0
    with open(os.path.join(out, "ocr_hard.csv"), "w", encoding="utf-8", newline="") as f, \
            open(os.path.join(out, "ocr_boxes_hard.jsonl"), "w", encoding="utf-8") as fb:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for k, r in enumerate(idm.itertuples()):
            p = os.path.join(root, orig.loc[r.image_id_old, "file"])
            sha = hashlib.sha1(open(p, "rb").read()).hexdigest()
            if sha != hard.loc[r.image_id, "sha1"]:
                raise SystemExit(f"해시 불일치: {p}")
            try:
                x = eng.run(p)
            except Exception as ex:
                fails += 1
                print("fail", r.image_id, type(ex).__name__, flush=True)
                continue
            w.writerow(dict(image_id=r.image_id, ocr_engine=eng.name, engine_version=eng.version, text=x["text"],
                            n_boxes=x["n_boxes"], conf_mean=x["conf_mean"]))
            fb.write(json.dumps(dict(image_id=r.image_id, boxes=x["boxes"]), ensure_ascii=False) + "\n")
            if k % 25 == 0:
                print(k, flush=True)
    print("끝", len(idm), "실패", fails, flush=True)


if __name__ == "__main__":
    main()
