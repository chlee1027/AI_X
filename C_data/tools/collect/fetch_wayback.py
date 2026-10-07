"""인터넷 아카이브(Wayback) 사본으로 페이지 원문을 받는다. 원 사이트에는 접속하지 않는다.

엔티티 인코딩 도박 광고가 든 페이지 가운데 일부는 페이지 전체가 도박 홍보라(넘어간 도메인)
직접 열지 않는다는 원칙을 지키려고 사본만 쓴다. 사본 원문은 `id_` 주소로 받는다(아카이브 도구 막대 없는 원문).
파이썬 urllib 는 아카이브가 429 로 막아 curl 을 쓰고, 요청 사이를 4초 띄운다.

사용: python tools/collect/fetch_wayback.py URL [URL ...]   (또는 @목록파일)
출력: data/raw/entity/pages/<host>_<시각>.html, 기록은 data/collection_log.csv 에 덧붙인다
"""
import csv
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse

ROOT = Path(__file__).resolve().parents[2]
PAGES = ROOT / "data" / "raw" / "entity" / "pages"
LOG = ROOT / "data" / "collection_log.csv"
ROUTE = "ETC 엔티티 인코딩 (Wayback 사본)"


def curl(url):
    time.sleep(4)
    r = subprocess.run(["curl", "-sL", "--compressed", "-A", "Mozilla/5.0", "--max-time", "120", url],
                       capture_output=True)
    return r.stdout


def fetch(url):
    # 조회는 CDX API 로 한다(available API 는 몰리면 빈 답을 준다). 상태 200 인 가장 최근 사본.
    snap = None
    for wait in (0, 20):
        time.sleep(wait)
        try:
            rows = json.loads(curl("https://web.archive.org/cdx/search/cdx?output=json&filter=statuscode:200"
                                   "&limit=-1&fl=timestamp,original&url=" + quote(url, safe="")) or b"[]")
        except json.JSONDecodeError:
            rows = []
        if len(rows) > 1:
            snap = {"timestamp": rows[-1][0]}
            break
    if not snap:
        return None, None, "no snapshot"
    ts = snap["timestamp"]
    raw = f"https://web.archive.org/web/{ts}id_/{url}"
    body = curl(raw)
    return ts, body, raw


def main(args):
    if args and args[0].startswith("@"):
        args = [l.strip() for l in Path(args[0][1:]).read_text(encoding="utf-8").splitlines() if l.strip()]
    PAGES.mkdir(parents=True, exist_ok=True)
    new_log = not LOG.exists()
    with LOG.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new_log:
            w.writerow(["collected_at", "route", "host", "url", "variant", "result", "count", "note"])
        for url in args:
            host = urlparse(url).hostname or url
            ts, body, note = fetch(url)
            now = datetime.now().isoformat(timespec="seconds")
            if body is None:
                w.writerow([now, ROUTE, host, url, "wayback", "none", 0, note])
                print(host, "사본 없음")
                continue
            path_part = re.sub(r"[^A-Za-z0-9]+", "_", urlparse(url).path).strip("_")
            name = f"{host}{'_' + path_part if path_part else ''}_{ts}.html"
            (PAGES / name).write_bytes(body)
            w.writerow([now, ROUTE, host, url, "wayback", 200, len(body), note])
            print(host, ts, len(body))


if __name__ == "__main__":
    main(sys.argv[1:])
