"""UA/Referer 조건별로 같은 URL 을 받아 원문 바이트를 그대로 저장한다 (ETC 클로킹 실사례 확인용).

- JS 를 실행하지 않는다 (requests). 해킹된 페이지의 스크립트가 돌지 않게 하려는 것.
- 리다이렉트를 따라가지 않는다. Location 헤더만 기록한다 (도박 도메인 접속 방지).
- 도메인당 순차 요청, 요청 간격 1.5초 이상, robots.txt 준수.

사용: python fetch_ua.py urls.txt out_dir [browser,googlebot,...]
"""
import csv
import hashlib
import json
import sys
import time
import urllib.robotparser
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlsplit

import requests

KST = timezone(timedelta(hours=9))
CRAWLER_ID = "TUK-AIHC-contest-datacollect/0.1"
VARIANTS = {
    "browser": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"},
    "browser_google_ref": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                         "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
                           "Referer": "https://www.google.com/"},
    "googlebot": {"User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"},
}
INTERVAL = 1.5

_robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}


# 도박 홍보 사이트 자체로 확인된 곳은 요청하지 않는다 (2026-10-04, magino.co.kr = 「온라인 홀덤사이트 - 인디고게임」)
BLOCKED_HOSTS = {"magino.co.kr"}


def robots_ok(url: str) -> bool:
    if (urlsplit(url).hostname or "").removeprefix("www.") in BLOCKED_HOSTS:
        return False
    p = urlsplit(url)
    origin = f"{p.scheme}://{p.netloc}"
    if origin not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = requests.get(origin + "/robots.txt", timeout=10, headers={"User-Agent": CRAWLER_ID})
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
        except requests.RequestException:
            rp.parse([])
        _robots[origin] = rp
        time.sleep(INTERVAL)
    return _robots[origin].can_fetch(CRAWLER_ID, url)


def main(url_file: str, out_dir: str, only: str = "") -> None:
    variants = {k: v for k, v in VARIANTS.items() if not only or k in only.split(",")}
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    log_path = out / "fetch_log.csv"
    new_log = not log_path.exists()
    with open(log_path, "a", newline="", encoding="utf-8") as lf:
        w = csv.writer(lf)
        if new_log:
            w.writerow(["fetched_at", "url", "variant", "status", "location", "bytes", "sha1", "file"])
        for url in [u.strip() for u in Path(url_file).read_text(encoding="utf-8-sig").splitlines()]:
            if not url or url.startswith("#"):
                continue
            if not robots_ok(url):
                w.writerow([datetime.now(KST).isoformat(), url, "-", "robots_disallow", "", 0, "", ""])
                continue
            key = hashlib.sha1(url.encode()).hexdigest()[:10]
            for name, headers in variants.items():
                try:
                    try:
                        r = requests.get(url, headers=headers, timeout=20, allow_redirects=False)
                    except requests.exceptions.SSLError:
                        # 국내 기관 사이트에 흔한 인증서 체인 누락. 읽기만 하므로 검증 없이 한 번 더
                        r = requests.get(url, headers=headers, timeout=20, allow_redirects=False, verify=False)
                    body = r.content
                    fname = f"{key}_{name}.html"
                    (out / fname).write_bytes(body)
                    meta = {"url": url, "variant": name, "status": r.status_code,
                            "headers": dict(r.headers), "request_headers": headers}
                    (out / f"{key}_{name}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1),
                                                          encoding="utf-8")
                    w.writerow([datetime.now(KST).isoformat(), url, name, r.status_code,
                                r.headers.get("Location", ""), len(body), hashlib.sha1(body).hexdigest(), fname])
                except requests.RequestException as e:
                    w.writerow([datetime.now(KST).isoformat(), url, name, f"error:{type(e).__name__}", "", 0, "", ""])
                lf.flush()
                time.sleep(INTERVAL)


if __name__ == "__main__":
    main(*sys.argv[1:4])
