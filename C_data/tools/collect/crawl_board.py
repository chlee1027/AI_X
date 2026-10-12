"""스팸이 쌓이는 게시판의 목록 페이지에서 최신 글을 따라가 원문을 받는다 (실측 수집용).

polite: robots.txt 준수 · 순차 요청 · 요청 간격 1.5초 · 게시판당 글 MAX_POSTS 개 · 쓰기/로그인/답글 링크 제외 · JS 실행 안 함
같은 호스트 링크만 따라간다 (스팸 글 안의 외부 도박 도메인으로는 가지 않는다).

사용: python crawl_board.py boards.txt out_dir [max_posts=12]
"""
import hashlib
import json
import re
import sys
import time
import urllib.robotparser
from datetime import datetime, timezone, timedelta
from html import unescape
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

import requests
import urllib3

urllib3.disable_warnings()
KST = timezone(timedelta(hours=9))
CRAWLER_ID = "TUK-AIHC-contest-datacollect/0.1"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/129.0.0.0 Safari/537.36")
INTERVAL = 1.5
POST = re.compile(r"wr_id=\d+|method=view&no=\d+|articleId=\d+|msg_seq=\d+|/article/[^\"']+/\d+/\d+|read\.html\?no=\d+|document_srl=\d+|"
                  r"[?&]uid=\d+|bmode=view|artclView\.do|mode=view|dataSid=\d+|nttId=\d+|/board_\w+/\d+", re.I)
SKIP = re.compile(r"write|login|logon|reply|password|delete|modify|w=u|w=r|member|sca=|sfl=|stx=|sst=|page=\d{2,}", re.I)
_robots: dict = {}


# 도박 홍보 사이트 자체로 확인된 곳은 요청하지 않는다 (2026-10-04, magino.co.kr = 「온라인 홀덤사이트 - 인디고게임」)
BLOCKED_HOSTS = {"magino.co.kr",
                 # 2026-10-10 사이트 이름이 「바다이야기사이트 릴게임사이트 …」인 같은 틀의 홍보 사이트(본문은 권한 오류 화면)
                 "withpmj.co.kr", "foodvvo.co.kr", "sweetkey.co.kr", "usanhyup.co.kr", "rockytour.co.kr", "imfunong.co.kr",
                 "kurozuya.co.kr", "gcymca.co.kr", "ickworld.co.kr", "nanjjang.kr", "madamwood.co.kr", "nihaojeju.co.kr",
                 "sunuro.co.kr", "00100.co.kr", "pbbs.co.kr", "namdotree.co.kr", "imreelpark.kr", "hosungomc.co.kr", "hongiksports.co.kr", "tntschool.com", "busan4989.co.kr",
                 "baramilboho.net"}  # 2026-10-10 사이트 이름 없이 낙태약·의약품 스팸 글만 있음(피해 게시판인지 가를 수 없어 제외)


def robots_ok(url: str) -> bool:
    if (urlsplit(url).hostname or "").removeprefix("www.") in BLOCKED_HOSTS:
        return False
    p = urlsplit(url)
    origin = f"{p.scheme}://{p.netloc}"
    if origin not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = requests.get(origin + "/robots.txt", timeout=10, headers={"User-Agent": CRAWLER_ID}, verify=False)
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
        except requests.RequestException:
            rp.parse([])
        _robots[origin] = rp
    return _robots[origin].can_fetch(CRAWLER_ID, url)


def get(url: str):
    try:
        return requests.get(url, headers={"User-Agent": UA}, timeout=20, allow_redirects=True)
    except requests.exceptions.SSLError:
        return requests.get(url, headers={"User-Agent": UA}, timeout=20, allow_redirects=True, verify=False)


def decode(r) -> str:
    raw = r.content
    m = re.search(rb"charset=[\"']?([\w-]+)", raw[:3000], re.I)
    enc = (m.group(1).decode() if m else r.apparent_encoding or "utf-8").lower()
    if enc in ("euc-kr", "ks_c_5601-1987"):
        enc = "cp949"
    try:
        return raw.decode(enc, "replace")
    except LookupError:  # charset 오타(uft-8 등)
        return raw.decode("utf-8", "replace")


DROP = {"page", "sst", "sod", "sop", "sfl", "stx", "device", "spt", "sca", "pageIndex", "startPage", "paging"}


def canonical(u: str) -> str:
    """정렬·쪽 번호 파라미터를 지워 같은 글을 한 주소로 (회차 사이 중복 방지)."""
    p = urlsplit(u)
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k not in DROP]
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(q), ""))


def with_page(board: str, pno: int) -> str:
    if pno == 1:
        return board
    p = urlsplit(board)
    q = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if k != "page"] + [("page", str(pno))]
    return urlunsplit((p.scheme, p.netloc, p.path, urlencode(q), ""))


def main(board_file: str, out_dir: str, max_posts: str = "12", pages: str = "1") -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    # 앞 회차(같은 상위 폴더의 r* 폴더)에서 이미 받은 글 키
    done_keys = {p.name.split("_")[0] for p in out.parent.glob("r*/*_browser.html")}
    log = open(out / "crawl_log.csv", "a", encoding="utf-8")
    boards = [b.strip() for b in Path(board_file).read_text(encoding="utf-8-sig").splitlines()
              if b.strip() and not b.startswith("#")]
    for board in boards:
        stamp = datetime.now(KST).isoformat(timespec="seconds")
        if not robots_ok(board):
            log.write(f"{stamp},list,{board},robots_disallow,0\n")
            continue
        links, seen = [], set()
        for pno in range(1, int(pages) + 1):
            list_url = with_page(board, pno)
            stamp = datetime.now(KST).isoformat(timespec="seconds")
            try:
                r = get(list_url)
            except requests.RequestException as e:
                log.write(f"{stamp},list,{list_url},error:{type(e).__name__},0\n")
                break
            html = decode(r)
            host = urlsplit(r.url).netloc
            before = len(links)
            for h in re.findall(r"href=[\"']([^\"'#]+)", html):
                u = canonical(urljoin(r.url, unescape(h)))
                if urlsplit(u).netloc != host or not POST.search(u) or SKIP.search(u) or u in seen:
                    continue
                seen.add(u)
                links.append(u)
            log.write(f"{stamp},list,{list_url},{r.status_code},{len(links) - before}\n")
            print(f"{list_url}  list={r.status_code} new_posts={len(links) - before}", flush=True)
            time.sleep(INTERVAL)
            if r.status_code != 200 or len(links) == before:
                break   # 더 넘길 쪽이 없으면 멈춘다
        for u in links[: int(max_posts)]:
            key = hashlib.sha1(u.encode()).hexdigest()[:10]
            if key in done_keys:   # 앞 회차에서 이미 받은 글은 건너뛴다
                continue
            done_keys.add(key)
            stamp = datetime.now(KST).isoformat(timespec="seconds")
            if not robots_ok(u):
                log.write(f"{stamp},post,{u},robots_disallow,0\n")
                continue
            try:
                pr = get(u)
            except requests.RequestException as e:
                log.write(f"{stamp},post,{u},error:{type(e).__name__},0\n")
                time.sleep(INTERVAL)
                continue
            text = decode(pr)
            (out / f"{key}_browser.html").write_text(text, encoding="utf-8")
            (out / f"{key}_browser.json").write_text(json.dumps({"url": u, "board": board, "status": pr.status_code,
                                                                 "fetched_at": stamp}, ensure_ascii=False),
                                                     encoding="utf-8")
            log.write(f"{stamp},post,{u},{pr.status_code},{len(pr.content)}\n")
            log.flush()
            time.sleep(INTERVAL)
    log.close()


if __name__ == "__main__":
    main(*sys.argv[1:5])
