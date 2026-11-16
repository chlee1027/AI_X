"""라벨 초안용 모아보기: 이미지 여러 장을 한 판(4x5)에 번호와 함께 붙인다.

입력: 이미지 파일 이름 목록(한 줄에 하나, collect/images 기준) 또는 --all
출력: logs/sheets/<이름>_NNN.png 와 <이름>_index.csv (sheet, cell, file)
성인 이미지는 수집 때 이미 걸렀으므로 여기 오지 않는다.
"""
import argparse
import csv
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
COLS, ROWS, TW, TH = 4, 5, 300, 170


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--images", default=os.path.join(HERE, "..", "collect", "images"))
    ap.add_argument("--list", default="")
    ap.add_argument("--name", default="sheet")
    ap.add_argument("--out", default=os.path.join(HERE, "..", "logs", "sheets"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    files = [l.strip() for l in open(a.list, encoding="utf-8") if l.strip()] if a.list else sorted(os.listdir(a.images))
    font = ImageFont.truetype("C:/Windows/Fonts/malgunbd.ttf", 14)
    per = COLS * ROWS
    idx = []
    for s in range(0, len(files), per):
        sheet = Image.new("RGB", (COLS * TW, ROWS * (TH + 20)), (235, 235, 235))
        d = ImageDraw.Draw(sheet)
        for c, fn in enumerate(files[s:s + per]):
            x, y = (c % COLS) * TW, (c // COLS) * (TH + 20)
            try:
                im = Image.open(os.path.join(a.images, fn))
                im.seek(0)
                im = im.convert("RGB")
                im.thumbnail((TW - 6, TH - 4))
                sheet.paste(im, (x + 3 + (TW - 6 - im.width) // 2, y + 20 + (TH - 4 - im.height) // 2))
            except Exception:
                d.text((x + 5, y + 60), "열기 실패", fill=(200, 0, 0), font=font)
            d.text((x + 4, y + 2), f"{c:02d} {fn[:16]}", fill=(0, 0, 160), font=font)
            d.rectangle([x, y, x + TW - 1, y + TH + 19], outline=(150, 150, 150))
            idx.append(dict(sheet=f"{a.name}_{s // per:03d}", cell=c, file=fn))
        sheet.save(os.path.join(a.out, f"{a.name}_{s // per:03d}.png"))
    with open(os.path.join(a.out, f"{a.name}_index.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["sheet", "cell", "file"])
        w.writeheader()
        w.writerows(idx)
    print(len(files), "images ->", (len(files) + per - 1) // per, "sheets")


if __name__ == "__main__":
    main()
