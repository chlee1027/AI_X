"""씨앗 목록 1: 1차 dev_data 의 출처 페이지(숨은 스팸이 실측된 피해 페이지) -> seeds_dev.csv

- 스팸이 있던(is_positive) 페이지가 있는 도메인만, 도메인마다 최대 2쪽(시드 0 무작위).
- 도메인 자체가 불법·스팸 업자 것으로 보이는 곳은 뺀다(피해 사이트까지만 연다는 원칙). 기준은 아래 두 가지:
  (1) 도메인 이름에 도박·성인 낱말이 있다(OFFSITE_RE)  (2) 손으로 본 목록 MANUAL_EXCLUDE (SEO 업자, 보안 업체 글, 질문 사이트 등
      피해 사이트가 아닌 곳). 단, 피해 기관 도메인 아래 해커가 만든 하위 도메인(s-togel.ksg.or.id 처럼)은 남긴다.
- site_type 은 도메인·경로로 정한 초안이다. 해킹·삽입형 홍보 페이지인지는 크롤 뒤 제목·본문 도박 낱말 수로 다시 본다.
"""
import csv
import json
import os
import html
import random
import re
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "logs", "dev_source_domains.json")
OUT = os.path.join(HERE, "..", "seeds_dev.csv")

OFFSITE_RE = re.compile(r"casino|toto|slot|bet|365|massage|kr365|seo|linkbuild|indexrotator", re.I)
VICTIM_SUFFIX = re.compile(r"\.(ac|go|sch|or|desa|gov|edu)\.[a-z]{2}$|\.(edu|gov)$|\.ac\.kr$|\.or\.kr$|\.go\.kr$|\.re\.kr$")
MANUAL_EXCLUDE = {"sucuri.net", "stackoverflow.com", "web.archive.org", "www.mdpabel.com", "bitflip.cc", "coinist.io",
                  "commu-test.com", "valid.global", "lp.lucasfelix.com", "sea-ex.com", "oloa36.com", "kfc1024.com",
                  "www.slotogram.com", "sengatanlebah.shop", "www.binaryuno.com", "www.ruyayorumu.net", "www.snappytv.com"}
BOARD_RE = re.compile(r"board|bbs|read\.html|view\.php|gall|community|kboard|wr_id|document_srl|article|forum|qna", re.I)


def site_type_of(host, path):
    if BOARD_RE.search(path):
        return "community"
    if re.search(r"\.(go|gov|desa)\.|\.gov$|\.go\.kr$|prefeitura", host):
        return "public"
    if re.search(r"\.(ac|edu|sch)\.|\.edu$|journal|jurnal|revista|ojs|ejournal|periodicos", host):
        return "university"
    return "other"


def main():
    dom = json.load(open(SRC, encoding="utf-8"))
    rng = random.Random(0)
    rows, excl = [], []
    for host in sorted(dom):
        pages = sorted({html.unescape(u) for u, p, _ in dom[host] if p})  # 1차 source 칸에 &amp; 가 섞여 있다
        if not pages:
            continue
        h = host.split(":")[0]
        if h in MANUAL_EXCLUDE or (OFFSITE_RE.search(h) and not VICTIM_SUFFIX.search(h)):
            excl.append(h)
            continue
        for u in rng.sample(pages, min(2, len(pages))):
            rows.append(dict(page_url=u, site_type=site_type_of(h, urlparse(u).path), origin="dev_data"))
    rng.shuffle(rows)
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["page_url", "site_type", "origin"])
        w.writeheader()
        w.writerows(rows)
    print("seeds", len(rows), "excluded domains", len(excl), excl)


if __name__ == "__main__":
    main()
