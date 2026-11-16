"""κ 표본 라벨용 엑셀과 되돌리기. 라벨 초안·출처·OCR 은 넣지 않는다(그림만 보고 판정).

만들기: python tools/kappa_xlsx.py make kappa_v1/meta_nolabel_343.csv kappa_v1 <출력.xlsx> --who 채현
되돌리기: python tools/kappa_xlsx.py export <입력.xlsx> <출력.csv>
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

LABELS = "illegal,legal_ad,campaign,normal"
SUBTYPES = "gambling,fake_doc,adult,sim_loan,drug,illegal_loan,other"
THUMB = 460
HELP = [
    "그림만 보고 판정합니다. 페이지·사이트·링크 정보는 쓰지 않습니다. 기준은 라벨 가이드라인 v1입니다.",
    "무엇을 파는지(A)와 홍보 단서(B: 사이트 이름·연락처·가입/보너스 문구)가 모두 보이면 illegal, unsure=0",
    "A나 B 하나만 보이면 unsure=1. 판단이 어려우면 오래 고민하지 말고 unsure=1 + note 한 줄",
    "subtype 은 illegal 일 때만 적습니다. unsure=1 이면 note 에 이유를 적습니다.",
    "외국어 글은 번역기로 확인합니다. 그림에 나온 주소·연락처에 접속하지 않습니다.",
]


def make(a):
    m = pd.read_csv(a.meta, dtype=str)
    wb = Workbook()
    ws = wb.active
    ws.title = "라벨"
    guide = wb.create_sheet("안내")
    guide.column_dimensions["A"].width = 110
    guide["A1"] = f"κ 라벨 ({a.who}) · {len(m)}장"
    guide["A1"].font = Font(bold=True)
    for i, t in enumerate(HELP, start=3):
        guide[f"A{i}"] = t
    guide[f"A{len(HELP) + 4}"] = "다 끝나면 '라벨' 탭의 노란 칸이 모두 찼는지 확인하고 저장합니다. 이 파일에는 이미지 축소본이 들어 있습니다."
    for c, (h, w) in zip("ABCDEF", [("image_id", 26), ("그림", 66), ("label", 12), ("subtype", 14), ("unsure", 9), ("note", 30)]):
        ws[f"{c}1"] = h
        ws[f"{c}1"].font = Font(bold=True)
        ws.column_dimensions[c].width = w
    ws.freeze_panes = "A2"
    yellow = PatternFill("solid", fgColor="FFF9C4")
    n = len(m) + 1
    for rng, vals in [(f"C2:C{n}", LABELS), (f"D2:D{n}", SUBTYPES), (f"E2:E{n}", "0,1")]:
        dv = DataValidation(type="list", formula1=f'"{vals}"', allow_blank=True)
        ws.add_data_validation(dv)
        dv.add(rng)
    for r, (_, row) in enumerate(m.iterrows(), start=2):
        ws[f"A{r}"] = row.image_id
        ws[f"A{r}"].alignment = Alignment(vertical="top", wrap_text=True)
        ws[f"E{r}"] = 0
        for c in "CDEF":
            ws[f"{c}{r}"].fill = yellow
            ws[f"{c}{r}"].alignment = Alignment(vertical="top", wrap_text=True)
        im = Image.open(os.path.join(a.root, row.file))
        im.seek(0)
        im = im.convert("RGB")
        im.thumbnail((THUMB, THUMB))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=85)
        buf.seek(0)
        x = XImage(buf)
        ws.add_image(x, f"B{r}")
        ws.row_dimensions[r].height = max(40, im.height * 0.76 + 6)
    wb.save(a.out)
    print("저장", a.out, len(m))


def export(a):
    wb = load_workbook(a.inp, data_only=True)
    ws = wb["라벨"]
    rows = []
    for r in ws.iter_rows(min_row=2, values_only=True):
        if not r[0]:
            continue
        rows.append(dict(image_id=r[0], label=r[2] or "", subtype=r[3] or "", unsure=int(r[4] or 0), note=r[5] or ""))
    d = pd.DataFrame(rows)
    d.to_csv(a.out, index=False, encoding="utf-8")
    print("행", len(d), "빈 라벨", int((d.label == "").sum()), d.label.value_counts().to_dict())


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("make")
    p.add_argument("meta")
    p.add_argument("root")
    p.add_argument("out")
    p.add_argument("--who", default="")
    p.set_defaults(fn=make)
    p = sub.add_parser("export")
    p.add_argument("inp")
    p.add_argument("out")
    p.set_defaults(fn=export)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
