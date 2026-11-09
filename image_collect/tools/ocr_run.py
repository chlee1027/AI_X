"""고정한 OCR 엔진(ocr_select/OCR_FIXED.txt)으로 collect/images 의 모든 이미지를 읽는다.

명세 6절 ocr.csv 형식(image_id 자리는 수집 중이라 파일 이름 file 을 쓰고, H2 export 때 image_id 로 바꾼다):
  collect/ocr_raw.csv        file, ocr_engine, engine_version, text, n_boxes, conf_mean
  collect/ocr_boxes.jsonl    한 줄에 이미지 하나: file, boxes
이미 읽은 파일은 건너뛴다(수집과 함께 여러 번 돌려도 된다).
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ocr_engines import Paddle  # noqa: E402
import safe_io  # noqa: E402

COL = os.path.join(HERE, "..", "collect")
COLS = ["file", "ocr_engine", "engine_version", "text", "n_boxes", "conf_mean"]


def main():
    # 사용: python ocr_run.py [샤드 번호 샤드 수]. 샤드마다 ocr_raw_<i>.csv, ocr_boxes_<i>.jsonl 에 쓰고 export 때 합친다
    shard, nsh = (int(sys.argv[1]), int(sys.argv[2])) if len(sys.argv) > 2 else (0, 1)
    sfx = f"_{shard}" if nsh > 1 else ""
    out_csv = os.path.join(COL, f"ocr_raw{sfx}.csv")
    box_path = os.path.join(COL, f"ocr_boxes{sfx}.jsonl")
    if safe_io.paused():
        print("PAUSE: 시작하지 않고 끝낸다", flush=True)
        return
    safe_io.repair_tail(out_csv)
    safe_io.repair_tail(box_path, quoted=False)
    done = set()
    for fn in os.listdir(COL):
        if fn.startswith("ocr_raw") and fn.endswith(".csv"):
            done |= {r["file"] for r in safe_io.read_csv(os.path.join(COL, fn))}
    files = [f for f in sorted(os.listdir(os.path.join(COL, "images"))) if ".tmp" not in f and f not in done]
    files = [f for i, f in enumerate(files) if i % nsh == shard]
    print("to read", len(files), flush=True)
    if not files:
        return
    eng = Paddle()
    new = not os.path.exists(out_csv) or os.path.getsize(out_csv) == 0
    with open(out_csv, "a", encoding="utf-8", newline="") as f, open(box_path, "a", encoding="utf-8") as fb:
        w = csv.DictWriter(f, fieldnames=COLS)
        if new:
            w.writeheader()
        for k, fn in enumerate(files):
            if safe_io.paused():
                print(f"PAUSE: {k}/{len(files)} 장에서 멈춘다", flush=True)
                break
            try:
                r = eng.run(os.path.join(COL, "images", fn))
            except Exception as ex:
                print("fail", fn, type(ex).__name__, flush=True)
                continue
            w.writerow(dict(file=fn, ocr_engine=eng.name, engine_version=eng.version, text=r["text"],
                            n_boxes=r["n_boxes"], conf_mean=r["conf_mean"]))
            fb.write(json.dumps(dict(file=fn, boxes=r["boxes"]), ensure_ascii=False) + "\n")
            f.flush()
            fb.flush()
            if k % 100 == 0:
                print(k, flush=True)


if __name__ == "__main__":
    main()
