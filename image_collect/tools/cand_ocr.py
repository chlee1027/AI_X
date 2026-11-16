"""후보 C: OCR 글에 도박·불법 홍보 낱말이 있는 이미지 중 아직 라벨이 없는 것 -> logs/cand_C_<n>.txt

낱말 목록은 1차 갈래 사전의 도박 쪽 핵심 낱말과, 표본 SA 에서 본 한국어 게시판 스팸 배너의 표지(가입코드, 텔레, 카톡 아이디, 총판 등)다.
OCR 오류로 「카지노」가 「카지 노」처럼 갈라지는 일이 있어 빈칸을 지운 글에서도 찾는다.
"""
import csv
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
COL = os.path.join(HERE, "..", "collect")
KW = re.compile(r"카지노|토토|슬롯|바카라|먹튀|홀덤|파워볼|배팅|베팅|꽁머니|가입코드|가입첫|첫충|매충|입플|총판|환전|충전|"
                r"텔레|카톡|라이브카지노|스포츠북|미니게임|입금|출금|롤링|페이백|"
                r"slot|gacor|togel|casino|judi|bandar|maxwin|scatter|pragmatic|sbobet|toto|baccarat|jackpot|"
                r"daftar|deposit|withdraw|bonus|wede|olympus|mahjong|bet", re.I)


def main():
    n = sys.argv[1] if len(sys.argv) > 1 else "1"
    labeled = set()
    p = os.path.join(COL, "labels_draft.csv")
    if os.path.exists(p):
        labeled = {r["file"] for r in csv.DictReader(open(p, encoding="utf-8"))}
    for f in glob.glob(os.path.join(HERE, "..", "logs", "cand_C_*.txt")):
        labeled |= set(open(f, encoding="utf-8").read().split())
    hits = []
    for f in glob.glob(os.path.join(COL, "ocr_raw*.csv")):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            t = r["text"]
            if r["file"] not in labeled and (KW.search(t) or KW.search(t.replace(" ", ""))):
                hits.append(r["file"])
    hits = sorted(set(hits))
    open(os.path.join(HERE, "..", "logs", f"cand_C_{n}.txt"), "w", encoding="utf-8").write("\n".join(hits))
    print("new C candidates", len(hits))


if __name__ == "__main__":
    main()
