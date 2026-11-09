"""도박 외 후보를 추려 모아보기 입력 목록을 만든다: logs/cand_NG_<n>.txt, logs/cand_NG_<n>.csv(후보별 근거).

후보 = 라벨이 없고, 아직 후보로 낸 적 없는 파일 중 하나를 만족.
  (가) 어느 사이트든 OCR 글이나 alt 에 도박 외 낱말이 있다. 도박·불법 홍보 표지 낱말(가입코드, 텔레, 카톡 등)도 스팸 게시판에서는 함께 본다.
  (나) 도박 외 씨앗(origin board_list, dev_nongamble, search_1104b)으로 연 페이지의 이미지 중 글 영역에 박힌 그림(화면 너비 100px 이상).
뉴스·쇼핑·금융·병원·공공 씨앗 이미지는 (가)에서도 OCR 도박 외 낱말이 있을 때만 후보로 둔다.
사용: python cand_nongamble.py <n>
"""
import csv
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import safe_io  # noqa: E402
from round_driver import TITLE, title_cat  # noqa: E402

COL = os.path.join(HERE, "..", "collect")
LOG = os.path.join(HERE, "..", "logs")
SPAM = re.compile(r"텔레|카톡|가입코드|총판|상담|문의|010|@\w+", re.I)
GEN = {"news", "shopping", "finance", "hospital", "public"}


def main():
    n = sys.argv[1]
    seen = set()
    for fn in ("labels_draft.csv", "labels_draft_add.csv"):
        seen |= {r["file"] for r in safe_io.read_csv(os.path.join(COL, fn))}
    for f in glob.glob(os.path.join(LOG, "cand_NG_*.txt")):
        seen |= set(open(f, encoding="utf-8").read().split())
    ocr = {}
    for f in glob.glob(os.path.join(COL, "ocr_raw*.csv")):
        for r in safe_io.read_csv(f):
            ocr[r["file"]] = r["text"]
    origin = {}
    for f in glob.glob(os.path.join(COL, "pages_*.csv")):
        for r in safe_io.read_csv(f):
            origin[r["page_url"]] = r["origin"].split(":")[0]
    cand = {}
    for f in glob.glob(os.path.join(COL, "occurrences_*.csv")):
        for r in safe_io.read_csv(f):
            fn = os.path.basename(r["file"])
            if fn in seen or fn in cand:
                continue
            t = ocr.get(fn, "")
            why = title_cat(t) or title_cat(t.replace(" ", "")) or title_cat(r["alt"])
            ng_page = origin.get(r["page_url"]) in ("board_list", "dev_nongamble", "search_1104b")
            if why:
                cand[fn] = (f"낱말:{why}", r["site"], r["site_type"], t[:60])
            elif ng_page and r["site_type"] not in GEN and fn in ocr and (SPAM.search(t) or len(re.findall(r"[가-힣]", t)) >= 4):  # 글 없는 그림, 보안문자(숫자), 짧은 로고는 뺀다
                cand[fn] = ("도박외 페이지", r["site"], r["site_type"], t[:60])
    names = sorted(cand, key=lambda f: (cand[f][1], f))
    open(os.path.join(LOG, f"cand_NG_{n}.txt"), "w", encoding="utf-8").write("\n".join(names))
    with open(os.path.join(LOG, f"cand_NG_{n}.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["file", "why", "site", "site_type", "ocr"])
        for fn in names:
            w.writerow([fn, *cand[fn]])
    from collections import Counter
    print(len(names), Counter(v[0] for v in cand.values()), Counter(v[2] for v in cand.values()))
    print(Counter(v[1] for v in cand.values()).most_common(15))
    print("OCR 읽은 파일", len(ocr))


if __name__ == "__main__":
    main()
