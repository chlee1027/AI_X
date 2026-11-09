"""라벨 확인용 엑셀: collect/labels_draft.csv 의 421장을 그림과 함께 한 파일에 담는다.

사용: python review_xlsx.py <출력 xlsx 경로>
탭: 시작(할 일, 판정 기준, 자동 집계) / 1_애매32 / 2_불법206 / 3_불법아님183
라벨·종류·애매 칸을 고치면 시작 탭의 집계가 다시 계산된다. 초안 값은 옆 칸에 그대로 남아 달라진 수를 센다.
웹에서 온 글(alt, OCR, 링크)은 수식으로 읽히지 않게 문자열로 고정하고 링크도 걸지 않는다.
"""
import csv
import glob
import io
import os
import re
import sys
from collections import defaultdict

from openpyxl import Workbook
from openpyxl.drawing.image import Image as XImage
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
COL = os.path.join(HERE, "..", "collect")
LABELS = "illegal,legal_ad,campaign,other"
CATS = "gambling,adult,forgery,loan,drug,invest,etc"
HEAD = ["번호", "그림", "확인(x)", "라벨", "종류", "애매(1)", "메모", "초안 라벨", "초안 종류", "초안 애매",
        "사이트", "찾은 경로", "그림 속 글(OCR)", "alt", "링크 주소(열지 말 것)", "파일"]
WIDTH = [6, 46, 8, 11, 11, 8, 24, 10, 10, 8, 24, 16, 50, 24, 40, 26]
SRC = {"B": "링크·주소·alt 낱말", "C": "OCR 낱말", "SA": "무작위 표본"}
BAD = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
EDIT = PatternFill("solid", fgColor="FFF4CC")
HEADF = PatternFill("solid", fgColor="E3EFED")
WRAP = Alignment(wrap_text=True, vertical="top")
BOLD = Font(bold=True)


def text(ws, cell, s):
    """웹에서 온 글을 수식이 아닌 문자열로 넣는다."""
    c = ws[cell]
    c.value = BAD.sub(" ", s or "")[:400]
    c.data_type = "s"
    c.alignment = WRAP


def thumb(path):
    with Image.open(path) as im:
        im.seek(0)
        im = im.convert("RGB")
        im.thumbnail((320, 150))
        b = io.BytesIO()
        im.save(b, "JPEG", quality=80)
    b.seek(0)
    return XImage(b), im.size


def load():
    lab = list(csv.DictReader(open(os.path.join(COL, "labels_draft.csv"), encoding="utf-8")))
    ocr = {}
    for f in glob.glob(os.path.join(COL, "ocr_raw*.csv")):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            ocr[r["file"]] = r["text"]
    occ = defaultdict(list)
    for f in glob.glob(os.path.join(COL, "occurrences_*.csv")):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            occ[os.path.basename(r["file"])].append(r)
    return lab, ocr, occ


def fill_tab(wb, title, rows, ocr, occ):
    ws = wb.create_sheet(title)
    for i, (h, w) in enumerate(zip(HEAD, WIDTH), 1):
        c = ws.cell(row=1, column=i, value=h)
        c.font, c.fill, c.alignment = BOLD, HEADF, WRAP
        ws.column_dimensions[c.column_letter].width = w
    ws.freeze_panes = "C2"
    rows = sorted(rows, key=lambda r: (first(occ, r, "site"), r["file"]))
    for n, r in enumerate(rows):
        y = n + 2
        fn = r["file"]
        unsure = int(r["unsure"])
        ws[f"A{y}"] = n + 1
        ws[f"D{y}"], ws[f"E{y}"], ws[f"F{y}"] = r["label"], r["category"] or None, unsure
        ws[f"H{y}"], ws[f"I{y}"], ws[f"J{y}"] = r["label"], r["category"] or None, unsure
        for col in "CDEFG":
            ws[f"{col}{y}"].fill = EDIT
        for col in "ACDEFGHIJ":
            ws[f"{col}{y}"].alignment = WRAP
        sites = sorted({o["site"] for o in occ.get(fn, [])})
        hrefs = [o["link_href"] for o in occ.get(fn, []) if o["link_href"]]
        alts = [o["alt"] for o in occ.get(fn, []) if o["alt"]]
        text(ws, f"K{y}", ", ".join(sites))
        text(ws, f"L{y}", SRC.get(r["source"], r["source"]))
        text(ws, f"M{y}", ocr.get(fn, ""))
        text(ws, f"N{y}", alts[0] if alts else "")
        text(ws, f"O{y}", hrefs[0] if hrefs else "")
        text(ws, f"P{y}", fn)
        ws.row_dimensions[y].height = 118
        try:
            img, _ = thumb(os.path.join(COL, "images", fn))
            ws.add_image(img, f"B{y}")
        except Exception:
            ws[f"B{y}"] = "그림 열기 실패, 파일 이름으로 확인"
    last = len(rows) + 1
    dv = DataValidation(type="list", formula1=f'"{LABELS}"', allow_blank=False)
    dc = DataValidation(type="list", formula1=f'"{CATS}"', allow_blank=True)
    du = DataValidation(type="list", formula1='"0,1"', allow_blank=False)
    for d, col in ((dv, "D"), (dc, "E"), (du, "F")):
        ws.add_data_validation(d)
        d.add(f"{col}2:{col}{last}")
    return last


def first(occ, r, key):
    o = occ.get(r["file"], [])
    return o[0][key] if o else ""


def start_tab(ws, tabs):
    def over(fmt):
        return "+".join(fmt.format(t=t, n=n) for t, n in tabs)
    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["C"].width = 80
    lines = [
        ("라벨 확인 (11.6 관문 전)", None, None),
        ("라벨 초안 421장은 Claude가 모아보기를 보고 판정한 것이다. 채현이 확인해야 라벨러 칸의 「채현」이 사실이 된다.", None, None),
        (None, None, None),
        ("할 일", None, None),
        ("1. 1_애매32 탭 32장을 본다 (11.6 전).", None, None),
        ("2. 2_불법206 탭은 11.6 전에 일부만 보고, 11.9 전에 전부 본다.", None, None),
        ("3. 3_불법아님183 탭은 불법을 놓치지 않았는지 볼 때 쓴다. 시간이 남으면 본다.", None, None),
        ("노란 칸만 고친다. 본 줄의 확인 칸에 x를 넣는다. 틀린 라벨은 라벨 칸을 바꾼다. 그 아래 집계가 저절로 바뀐다.", None, None),
        ("링크 주소는 불법 사이트일 수 있으니 열지 않는다. 다 본 뒤 저장하고 Claude에게 「다 봤어」라고 하면 labels_draft.csv에 반영한다.", None, None),
        (None, None, None),
    ]
    rows = [
        ("자동 집계", "지금 값", "설명"),
        ("불법(illegal)", "=" + over("COUNTIF('{t}'!D2:D{n},\"illegal\")"), "초안 238. 관문 기준은 100장 이상"),
        ("  확실 (애매 0)", "=" + over("COUNTIFS('{t}'!D2:D{n},\"illegal\",'{t}'!F2:F{n},0)"), "초안 206"),
        ("  애매 (애매 1)", "=" + over("COUNTIFS('{t}'!D2:D{n},\"illegal\",'{t}'!F2:F{n},1)"), "초안 32"),
        ("관문 판정", '=IF(B{ill}>=100,"100장 이상","100장 미만")', "100장 이상이면 계획 A, 미만이면 계획 B"),
        ("확인한 장수", "=" + over("COUNTIF('{t}'!C2:C{n},\"?*\")"), "전체 421장 중"),
        ("초안과 달라진 장수", "=" + over("SUMPRODUCT(--((('{t}'!D2:D{n}<>'{t}'!H2:H{n})+('{t}'!E2:E{n}<>'{t}'!I2:I{n})+('{t}'!F2:F{n}<>'{t}'!J2:J{n}))>0))"), "라벨·종류·애매 중 하나라도 바뀐 줄"),
    ]
    guide = [
        ("칸 값", None, None),
        ("라벨", "illegal", "불법광고"),
        ("", "legal_ad", "합법 상품 광고 (복권, 은행, 학교 과정 등)"),
        ("", "campaign", "계도 포스터 (불법 도박 근절 등)"),
        ("", "other", "그 밖의 모든 것 (피해 사이트 자신의 로고·사진·버튼 등)"),
        ("종류 (불법일 때만)", "gambling", "도박"),
        ("", "adult", "성인 (060 폰팅 등)"),
        ("", "forgery", "대리시험·위조 문서"),
        ("", "loan", "불법 대출 (선불유심 내구제 등)"),
        ("", "drug", "의약품 판매"),
        ("", "invest", "투자 사기"),
        ("", "etc", "그 밖의 불법 홍보"),
        (None, None, None),
        ("Claude가 쓴 임시 기준 (준아의 가이드라인 v1이 오면 그쪽을 따른다)", None, None),
        ("불법, 애매 0", "", "도박 사이트 이름·로고, 가입·보너스·충전 같은 홍보 문구, 도박 사이트 화면, 라이브 카지노 딜러 홍보 그림"),
        ("불법, 애매 1", "", "슬롯 게임 제목 그림만 있고 사이트·홍보 문구가 없는 것, 칩·슬롯 아이콘, 「DAFTAR SEKARANG」 같은 가입 단추만 있는 것, 일부만 보이는 로고"),
        ("불법 아님", "", "빈 그림, 아이콘, 피해 사이트 자신의 사진"),
    ]
    y = 1
    for a, b, c in lines:
        ws[f"A{y}"] = a
        if a:
            ws.merge_cells(f"A{y}:C{y}")
            ws[f"A{y}"].alignment = WRAP
            ws.row_dimensions[y].height = 18 if len(a) < 70 else 34
        if a in ("라벨 확인 (11.6 관문 전)", "할 일"):
            ws[f"A{y}"].font = BOLD
        y += 1
    ill = y + 1
    for i, (a, b, c) in enumerate(rows):
        ws[f"A{y}"], ws[f"C{y}"] = a, c
        ws[f"B{y}"] = b.format(ill=ill) if "{ill}" in b else b
        if i == 0:
            for col in "ABC":
                ws[f"{col}{y}"].font, ws[f"{col}{y}"].fill = BOLD, HEADF
        y += 1
    y += 1
    for a, b, c in guide:
        ws[f"A{y}"], ws[f"B{y}"], ws[f"C{y}"] = a, b, c
        ws[f"C{y}"].alignment = WRAP
        if a and b is None:
            ws[f"A{y}"].font = BOLD
            ws.merge_cells(f"A{y}:C{y}")
        y += 1


def main():
    out = sys.argv[1]
    lab, ocr, occ = load()
    a = [r for r in lab if r["label"] == "illegal" and r["unsure"] == "1"]
    b = [r for r in lab if r["label"] == "illegal" and r["unsure"] != "1"]
    c = [r for r in lab if r["label"] != "illegal"]
    names = (f"1_애매{len(a)}", f"2_불법{len(b)}", f"3_불법아님{len(c)}")
    wb = Workbook()
    start = wb.active
    start.title = "시작"
    tabs = [(t, fill_tab(wb, t, rows, ocr, occ)) for t, rows in zip(names, (a, b, c))]
    start_tab(start, tabs)
    wb.save(out)
    print(out, [(t, n - 1) for t, n in tabs], f"{os.path.getsize(out) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
