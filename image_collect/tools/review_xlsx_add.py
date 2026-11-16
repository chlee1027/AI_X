"""추가 수집 라벨 확인용 엑셀: collect/labels_draft_add.csv 의 행을 그림과 함께 담는다. 기존 라벨확인 파일과 별개다.

사용: python review_xlsx_add.py <출력 xlsx 경로>
탭: 시작 / 1_애매 / 2_불법 / 3_불법아님. 칸과 자동 집계는 review_xlsx.py 와 같다. 넣는 이미지는 수집한 파일의 축소본뿐이다.
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import safe_io  # noqa: E402
from openpyxl import Workbook  # noqa: E402
from openpyxl.styles import Alignment, Font, PatternFill  # noqa: E402
from review_xlsx import COL, fill_tab, load  # noqa: E402

BOLD = Font(bold=True)
HEADF = PatternFill("solid", fgColor="E3EFED")
WRAP = Alignment(wrap_text=True, vertical="top")


def start_tab(ws, tabs, counts):
    def over(fmt):
        return "+".join(fmt.format(t=t, n=n) for t, n in tabs)
    ws.column_dimensions["A"].width = 34
    ws.column_dimensions["B"].width = 16
    ws.column_dimensions["C"].width = 80
    y = 1
    for text, bold in [
        ("추가 수집 라벨 확인", True),
        (f"11-04~11-05 추가 수집분의 라벨 초안 {counts['illegal'] + counts['rest']}장이다. 모두 Claude가 모아보기를 보고 판정했고 라벨러 칸이 「Claude초안」이다.", False),
        ("할 일: 1_애매 탭, 2_불법 탭, 3_불법아님 탭 순서로 본다. 노란 칸만 고치고, 본 줄의 확인 칸에 x를 넣는다.", False),
        ("링크 주소는 불법 사이트일 수 있으니 열지 않는다. 그림에 나온 연락처로 연락하지 않는다. 다 본 뒤 저장하고 Claude에게 알리면 라벨 파일에 반영한다.", False),
        ("이 파일에는 이미지 축소본이 들어 있어 H2(11.9) 때 지운다.", False),
    ]:
        ws[f"A{y}"] = text
        ws.merge_cells(f"A{y}:C{y}")
        ws[f"A{y}"].alignment = WRAP
        ws.row_dimensions[y].height = 18 if len(text) < 70 else 34
        if bold:
            ws[f"A{y}"].font = BOLD
        y += 2 if y == 1 else 1
    y += 1
    rows = [("자동 집계", "지금 값", "설명"),
            ("추가분 불법(illegal)", "=" + over("COUNTIF('{t}'!D2:D{n},\"illegal\")"), f"초안 {counts['illegal']}. 기존 확인분 238장은 이 파일에 없다"),
            ("  애매 (애매 1)", "=" + over("COUNTIFS('{t}'!D2:D{n},\"illegal\",'{t}'!F2:F{n},1)"), f"초안 {counts['unsure']}"),
            ("확인한 장수", "=" + over("COUNTIF('{t}'!C2:C{n},\"?*\")"), f"전체 {sum(counts[k] for k in ('illegal', 'rest'))}장 중"),
            ("초안과 달라진 장수", "=" + over("SUMPRODUCT(--((('{t}'!D2:D{n}<>'{t}'!H2:H{n})+('{t}'!E2:E{n}<>'{t}'!I2:I{n})+('{t}'!F2:F{n}<>'{t}'!J2:J{n}))>0))"), "라벨·종류·애매 중 하나라도 바뀐 줄")]
    for c in ("gambling", "adult", "loan", "drug", "invest", "forgery", "etc"):
        rows.append((f"  종류 {c}", "=" + over("COUNTIFS('{t}'!D2:D{n},\"illegal\",'{t}'!E2:E{n},\"" + c + "\")"), f"초안 {counts['cat_' + c]}"))
    for i, (a, b, c) in enumerate(rows):
        ws[f"A{y}"], ws[f"B{y}"], ws[f"C{y}"] = a, b, c
        if i == 0:
            for col in "ABC":
                ws[f"{col}{y}"].font, ws[f"{col}{y}"].fill = BOLD, HEADF
        y += 1
    y += 1
    for a, b, c in [("Claude가 쓴 임시 기준 (준아의 가이드라인 v1이 오면 그쪽을 따른다)", None, None),
                    ("loan", "", "내구제, 소액결제·정보이용료·신용카드 현금화"), ("forgery", "", "대리시험, 서류·증명서 위조"),
                    ("drug", "", "의약품 판매. 제품·알약 사진만 있고 판매 문구가 없으면 애매"), ("adult", "", "060 폰팅, 유흥, 출장, 도우미 모집"),
                    ("invest", "", "주식·코인 정보방 유인, 코인 승부 게임. 코인 환전 포스터는 애매"), ("etc", "", "불법 홍보 대행, 짝퉁 도매 등"),
                    ("gambling", "", "도박 사이트, 도박 솔루션 분양")]:
        ws[f"A{y}"], ws[f"B{y}"], ws[f"C{y}"] = a, b, c
        ws[f"C{y}"].alignment = WRAP
        if b is None:
            ws[f"A{y}"].font = BOLD
            ws.merge_cells(f"A{y}:C{y}")
        y += 1


def main():
    out = sys.argv[1]
    _, ocr, occ = load()
    add = safe_io.read_csv(os.path.join(COL, "labels_draft_add.csv"))
    a = [r for r in add if r["label"] == "illegal" and r["unsure"] == "1"]
    b = [r for r in add if r["label"] == "illegal" and r["unsure"] != "1"]
    c = [r for r in add if r["label"] != "illegal"]
    names = (f"1_애매{len(a)}", f"2_불법{len(b)}", f"3_불법아님{len(c)}")
    wb = Workbook()
    start = wb.active
    start.title = "시작"
    tabs = [(t, fill_tab(wb, t, rows, ocr, occ)) for t, rows in zip(names, (a, b, c))]
    cat = Counter(r["category"] for r in a + b)
    counts = Counter(illegal=len(a) + len(b), unsure=len(a), rest=len(c))
    for k, v in cat.items():
        counts["cat_" + k] = v
    start_tab(start, tabs, counts)
    wb.save(out)
    print(out.encode("ascii", "replace").decode(), [(t.encode("ascii", "replace").decode(), n - 1) for t, n in tabs], dict(cat), f"{os.path.getsize(out) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
