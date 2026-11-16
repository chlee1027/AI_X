"""초안 점검용 엑셀과 집계. 점검 표본 200장(불법 초안 100, normal 초안 100)을 그림과 초안 라벨로 보여 준다.

만들기: python tools/check_xlsx.py make deliver/check_sample.csv collect/images <출력.xlsx>
집계:   python tools/check_xlsx.py score <입력.xlsx> <출력.csv>
"""
import argparse
import io
import os

import pandas as pd
from openpyxl import Workbook, load_workbook
from openpyxl.drawing.image import Image as XImage
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from PIL import Image

THUMB = 460
LABELS = "illegal,legal_ad,campaign,normal"
HELP = [
    "판정 칸은 비어 있습니다. 한 줄씩 그림을 보고 맞음, 틀림, 모름 중 하나를 고릅니다. 틀림이면 맞는 라벨도 고릅니다.",
    "판단이 어려우면 '모름'을 고릅니다. 오래 고민하지 않아도 됩니다. 모름과 빈 칸은 오류율에서 뺍니다.",
    "맞음이 많으면 첫 줄에 맞음을 고른 뒤 복사해서 붙여 넣어도 되지만, 본 줄에만 하고 안 본 줄은 비워 둡니다.",
    "OCR 칸은 기계가 읽은 글이라 틀릴 수 있습니다. 외국어는 번역기로 확인합니다.",
    "링크나 그림 속 주소·연락처에 접속하지 않습니다. 이 파일에는 이미지 축소본이 들어 있어 H2 때 지웁니다.",
]


def make(a):
    m = pd.read_csv(a.sample, dtype=str).fillna("")
    ocr = pd.read_csv("deliver/for_junah/ocr.csv", dtype=str).fillna("").set_index("image_id")["text"]
    wb = Workbook()
    ws = wb.active
    ws.title = "점검"
    g = wb.create_sheet("안내")
    g.column_dimensions["A"].width = 110
    g["A1"] = f"초안 점검 {len(m)}장"
    g["A1"].font = Font(bold=True)
    for i, t in enumerate(HELP, start=3):
        g[f"A{i}"] = t
    heads = [("image_id", 26), ("그림", 66), ("초안", 12), ("OCR", 34), ("판정", 9), ("맞는 라벨", 12), ("메모", 24)]
    for c, (h, w) in zip("ABCDEFG", heads):
        ws[f"{c}1"] = h
        ws[f"{c}1"].font = Font(bold=True)
        ws.column_dimensions[c].width = w
    ws.freeze_panes = "A2"
    n = len(m) + 1
    for rng, vals in [(f"E2:E{n}", "맞음,틀림,모름"), (f"F2:F{n}", LABELS)]:
        dv = DataValidation(type="list", formula1=f'"{vals}"', allow_blank=True)
        ws.add_data_validation(dv)
        dv.add(rng)
    yellow = PatternFill("solid", fgColor="FFF9C4")
    wrap = Alignment(vertical="top", wrap_text=True)
    for r, (_, row) in enumerate(m.iterrows(), start=2):
        ws[f"A{r}"] = row.image_id
        ws[f"C{r}"] = row.label + (f"\n{row.subtype}" if row.subtype else "") + ("\nunsure=1" if row.unsure == "1" else "")
        ws[f"D{r}"] = ocr.get(row.image_id, "")[:300]
        for c in "ACD":
            ws[f"{c}{r}"].alignment = wrap
        for c in "EFG":
            ws[f"{c}{r}"].fill = yellow
            ws[f"{c}{r}"].alignment = wrap
        im = Image.open(os.path.join(a.images, row.file_old))
        im.seek(0)
        im = im.convert("RGB")
        im.thumbnail((THUMB, THUMB))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=85)
        buf.seek(0)
        ws.add_image(XImage(buf), f"B{r}")
        ws.row_dimensions[r].height = max(60, im.height * 0.76 + 6)
    wb.save(a.out)
    print("저장", a.out, len(m))


def score(a):
    wb = load_workbook(a.inp, data_only=True)
    rows = []
    for r in wb["점검"].iter_rows(min_row=2, values_only=True):
        if r[0]:
            rows.append(dict(image_id=r[0], draft=str(r[2]).split("\n")[0], verdict=r[4] or "", correct=r[5] or "", memo=r[6] or ""))
    d = pd.DataFrame(rows)
    d.to_csv(a.out, index=False, encoding="utf-8")
    print("안 본 줄", int((d.verdict == "").sum()), "모름", int((d.verdict == "모름").sum()))
    for lab, g in d.groupby("draft"):
        known = g[g.verdict.isin(["맞음", "틀림"])]
        n, wrong = len(known), int((known.verdict == "틀림").sum())
        if n == 0:
            print(lab, "본 줄 없음")
            continue
        hi = 3 / n if wrong == 0 else None  # 틀림 0 이면 95% 상한은 약 3/n
        print(lab, "본 줄", n, "틀림", wrong, f"오류율 {wrong / n:.1%}", f"(틀림 0 이어도 상한 약 {hi:.1%})" if hi else "")


def main():
    ap = argparse.ArgumentParser()
    s = ap.add_subparsers(dest="cmd", required=True)
    p = s.add_parser("make")
    p.add_argument("sample")
    p.add_argument("images")
    p.add_argument("out")
    p.set_defaults(fn=make)
    p = s.add_parser("score")
    p.add_argument("inp")
    p.add_argument("out")
    p.set_defaults(fn=score)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
