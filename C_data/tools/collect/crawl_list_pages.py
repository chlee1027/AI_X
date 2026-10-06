"""스팸이 쌓인 게시판의 목록 페이지만 1..N 쪽 받는다 (글 본문은 안 연다, 실측 수집용).

HOMOGLYPH 보충용(2026-10-06). 스팸 글 제목에 위장 문자가 그대로 들어 있어 목록 페이지만으로 충분하다.
polite: robots.txt 준수 · 순차 요청 · 요청 간격 1.5초 · 403/429 는 그 게시판 중단 · JS 실행 안 함 · 외부 링크 안 따라감

boards 파일: 한 줄에 목록 주소 하나, 쪽 번호 자리는 {page}.
사용: python tools/collect/crawl_list_pages.py boards.txt out_dir [pages=40]
"""
import hashlib
import json
import sys
import time
import urllib.robotparser
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlsplit

import requests
import urllib3

urllib3.disable_warnings()
KST = timezone(timedelta(hours=9))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/129.0.0.0 Safari/537.36")
INTERVAL = 1.5
_robots: dict = {}


def robots_ok(url: str) -> bool:
    p = urlsplit(url)
    origin = f"{p.scheme}://{p.netloc}"
    if origin not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = requests.get(origin + "/robots.txt", timeout=10, headers={"User-Agent": UA}, verify=False)
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
        except requests.RequestException:
            rp.parse([])
        _robots[origin] = rp
    return _robots[origin].can_fetch(UA, url)


def main(boards: str, out_dir: str, pages: int = 40) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    log = (out / "log.jsonl").open("a", encoding="utf-8")
    for tpl in [x.strip() for x in Path(boards).read_text(encoding="utf-8").splitlines() if x.strip() and not x.startswith("#")]:
        for n in range(1, pages + 1):
            url = tpl.format(page=n)
            rec = {"at": datetime.now(KST).isoformat(timespec="seconds"), "url": url}
            if not robots_ok(url):
                rec["result"] = "robots"
                log.write(json.dumps(rec, ensure_ascii=False) + "\n")
                break
            try:
                r = requests.get(url, timeout=30, headers={"User-Agent": UA}, verify=False)
                rec["result"] = r.status_code
                if r.status_code in (403, 429):
                    log.write(json.dumps(rec, ensure_ascii=False) + "\n")
                    break
                if r.status_code == 200:
                    pid = hashlib.sha1(url.encode()).hexdigest()[:12]
                    (out / f"{pid}.html").write_bytes(r.content)
                    rec.update(page_id=pid, bytes=len(r.content))
            except requests.RequestException as e:
                rec["result"] = f"error {type(e).__name__}"
            log.write(json.dumps(rec, ensure_ascii=False) + "\n")
            log.flush()
            time.sleep(INTERVAL)
    log.close()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 40)
