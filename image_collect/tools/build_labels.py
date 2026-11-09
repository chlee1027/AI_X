"""라벨 초안 모으기: labels_B.py 등의 판·칸 표기를 파일 이름으로 바꿔 collect/labels_draft.csv 를 쓴다.

열: file, label, category, unsure, lang, labeler, source(어느 후보 묶음에서 봤는지)
- S -> illegal/unsure 0, U -> illegal/unsure 1 (category 는 cat 칸, 없으면 gambling), LS -> legal_ad/unsure 0, OU -> other/unsure 1, LU -> legal_ad/unsure 1, 나머지 칸 -> other/unsure 0
- 같은 파일이 여러 묶음에 나오면 먼저 본 묶음(아래 순서)을 따른다
- lang 은 명세상 눈으로 정하는 칸이지만, 초안은 OCR 글로 채운다(한글만 ko, 라틴만 en 또는 id, 둘 다 mixed, 글 없음 none).
  인도네시아어 표지 낱말이 있으면 id. 채현이 라벨 확인 때 고친다.
"""
import csv
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
COL = os.path.join(HERE, "..", "collect")
SHEETS = os.path.join(HERE, "..", "logs", "sheets")
ID_WORDS = re.compile(r"\b(daftar|sekarang|situs|terpercaya|gacor|wajib|hari|ini|akun|baru|resmi|pasti|bayar|gabung|disini|dengan|dan|yang|untuk)\b", re.I)


def ocr_text():
    t = {}
    for f in glob.glob(os.path.join(COL, "ocr_raw*.csv")):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            t[r["file"]] = r["text"]
    return t


def lang_of(s):
    if not s or not s.strip():
        return "none"
    ko = bool(re.search(r"[가-힣]", s))
    lat = bool(re.search(r"[A-Za-z]{3,}", s))
    if ko and lat:
        return "mixed"
    if ko:
        return "ko"
    if re.search(r"[一-鿿]", s) and not lat:
        return "zh"
    if lat:
        return "id" if ID_WORDS.search(s) else "en"
    return "none"


def main():
    import labels_B
    groups = [("B", labels_B.B), ("SA", labels_B.SA)]
    try:
        import labels_C
        groups.append(("C", labels_C.C))
    except ImportError:
        pass
    idx = {}
    for f in glob.glob(os.path.join(SHEETS, "*_index.csv")):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            idx[(r["sheet"], int(r["cell"]))] = r["file"]
    txt = ocr_text()
    out, seen = [], set()
    for gname, g in groups:
        for sheet, d in g.items():
            cells = [c for (s, c) in idx if s == sheet]
            for c in sorted(cells):
                fn = idx[(sheet, c)]
                if fn in seen:
                    continue
                seen.add(fn)
                cat = d.get("cat", {}).get(c, "gambling")
                if c in d.get("S", []):
                    lab = ("illegal", cat, 0)
                elif c in d.get("U", []):
                    lab = ("illegal", cat, 1)
                elif c in d.get("LS", []):
                    lab = ("legal_ad", "", 0)
                elif c in d.get("LU", []):
                    lab = ("legal_ad", "", 1)
                elif c in d.get("OU", []):
                    lab = ("other", "", 1)
                else:
                    lab = ("other", "", 0)
                out.append(dict(file=fn, label=lab[0], category=lab[1], unsure=lab[2], lang=lang_of(txt.get(fn, "")),
                                labeler="채현", source=gname))
    with open(os.path.join(COL, "labels_draft.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["file", "label", "category", "unsure", "lang", "labeler", "source"])
        w.writeheader()
        w.writerows(out)
    from collections import Counter
    print(len(out), Counter((r["source"], r["label"], r["unsure"]) for r in out))


if __name__ == "__main__":
    main()
