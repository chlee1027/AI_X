"""data/collection_log.csv 작성: 대상·일시·건수 (기획서 신뢰도 근거).

fetch_ua.py 의 fetch_log.csv 와 dump_hidden.py 의 dump_log.csv 를 합친다.
사용: python make_collection_log.py data_dir
"""
import csv
import sys
from pathlib import Path
from urllib.parse import urlsplit


def main(data_dir: str) -> None:
    d = Path(data_dir)
    rows = []
    for f in sorted(d.glob("raw/etc/r*/fetch_log.csv")):
        for r in csv.DictReader(open(f, encoding="utf-8")):
            rows.append({"collected_at": r["fetched_at"][:19], "route": "ETC 클로킹 확인 (UA·Referer 변형 원문 수집)",
                         "host": urlsplit(r["url"]).netloc, "url": r["url"], "variant": r["variant"],
                         "result": r["status"], "count": r["bytes"], "note": r["location"]})
    for f in sorted(d.glob("raw/decoy/r*/dump_log.csv")):
        for line in open(f, encoding="utf-8"):
            p = line.rstrip("\n").split(",")
            if len(p) < 4:
                continue
            rows.append({"collected_at": p[0][:19], "route": "DECOY 숨김 요소 덤프 (Playwright polite)",
                         "host": urlsplit(p[1]).netloc, "url": p[1], "variant": "edge-headless",
                         "result": p[2], "count": p[3], "note": f"hidden={p[4]}" if len(p) > 4 else ""})
    for f in sorted(d.glob("raw/etc/r*/crawl_log.csv")):
        for line in open(f, encoding="utf-8"):
            p = line.rstrip("\n").split(",")
            if len(p) < 5:
                continue
            rows.append({"collected_at": p[0][:19], "route": f"게시판 크롤 ({p[1]})",
                         "host": urlsplit(p[2]).netloc, "url": p[2], "variant": "browser",
                         "result": p[3], "count": p[4], "note": ""})
    out = d / "collection_log.csv"
    with open(out, "w", newline="", encoding="utf-8") as fo:
        w = csv.DictWriter(fo, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: r["collected_at"]))
    print(out, len(rows), "행")


if __name__ == "__main__":
    main(sys.argv[1])
