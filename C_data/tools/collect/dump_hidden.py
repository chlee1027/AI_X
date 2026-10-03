"""숨김 신호 요소 덤프 스크립트 (Playwright 단독, polite 모드).

시드 URL 마다 그 페이지와 같은 호스트의 링크 몇 개를 렌더링하고, probe_hidden.js 로
- 숨김 신호가 있는 텍스트 요소 (DECOY·ETC 후보)
- 위험 어휘가 든 보이는 텍스트 요소 (risky_word_normal·policy_text 후보)
를 JSON 으로 남긴다. 판정(광고인가 아닌가)은 하지 않는다. 그건 사람이 한다.

polite: robots.txt 준수 · 순차 요청 · 요청 간격 1.5초 · 로그인 영역 제외 · 이미지/폰트/미디어 차단

사용: python dump_hidden.py seeds.txt out_dir [pages_per_seed=3]
"""
import json
import re
import sys
import time
import urllib.robotparser
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests
from playwright.sync_api import sync_playwright

KST = timezone(timedelta(hours=9))
CRAWLER_ID = "TUK-AIHC-contest-datacollect/0.1"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/129.0.0.0 Safari/537.36 " + CRAWLER_ID)
INTERVAL = 1.5
RISKY = ["환전", "상담", "보너스", "지급", "무료 체험", "무료체험", "도박", "카지노", "베팅", "배팅", "토토",
         "바로가기", "가입", "코드", "텔레그램", "적립", "포인트", "이벤트", "당첨", "경품", "사행", "슬롯", "복권"]
LOGIN_HINT = re.compile(r"login|logon|signin|member|mypage|auth|sso|join", re.I)
PROBE = (Path(__file__).parent / "probe_hidden.js").read_text(encoding="utf-8")

_robots: dict = {}


def robots_ok(url: str) -> bool:
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
    return _robots[origin].can_fetch(CRAWLER_ID, url)


def pick_links(page, base: str, n: int) -> list[str]:
    host = urlsplit(base).netloc
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.getAttribute('href'))")
    scored = []
    for h in hrefs:
        if not h or h.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue
        u = urljoin(base, h).split("#")[0]
        if urlsplit(u).netloc != host or LOGIN_HINT.search(u) or re.search(r"\.(pdf|hwp|zip|jpg|png|xlsx?)$", u, re.I):
            continue
        score = 2 if re.search(r"board|bbs|notice|view|list|faq|guide|info|sub", u, re.I) else 1
        scored.append((score, u))
    seen, out = set(), []
    for _, u in sorted(scored, key=lambda x: -x[0]):
        if u not in seen and u != base:
            seen.add(u)
            out.append(u)
        if len(out) >= n:
            break
    return out


def main(seed_file: str, out_dir: str, pages_per_seed: str = "3") -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    seeds = [s.strip() for s in Path(seed_file).read_text(encoding="utf-8-sig").splitlines()
             if s.strip() and not s.startswith("#")]
    log = open(out / "dump_log.csv", "a", encoding="utf-8")
    with sync_playwright() as p:
        # 번들 Chromium 다운로드가 막혀 있어 시스템 Edge(같은 Chromium 엔진)를 쓴다
        browser = p.chromium.launch(channel="msedge", args=["--disable-web-security", "--disable-gpu"])
        ctx = browser.new_context(user_agent=UA, ignore_https_errors=True, viewport={"width": 1280, "height": 900},
                                  locale="ko-KR")
        ctx.route("**/*", lambda r: r.abort() if r.request.resource_type in ("image", "media", "font") else r.continue_())
        page = ctx.new_page()
        for seed in seeds:
            queue, done = [seed], 0
            while queue and done < int(pages_per_seed):
                url = queue.pop(0)
                stamp = datetime.now(KST).isoformat(timespec="seconds")
                if not robots_ok(url):
                    log.write(f"{stamp},{url},robots_disallow,0\n")
                    continue
                try:
                    page.goto(url, wait_until="load", timeout=20000)
                    page.wait_for_timeout(800)
                    items = page.evaluate(PROBE, {"riskyWords": RISKY})
                except Exception as e:  # noqa: BLE001
                    log.write(f"{stamp},{url},error:{type(e).__name__},0\n")
                    time.sleep(INTERVAL)
                    continue
                key = re.sub(r"[^A-Za-z0-9]+", "_", urlsplit(url).netloc + urlsplit(url).path)[:60] + f"_{done}"
                (out / f"{key}.json").write_text(json.dumps({"url": page.url, "requested": url, "fetched_at": stamp,
                                                             "title": page.title(), "items": items},
                                                            ensure_ascii=False, indent=1), encoding="utf-8")
                n_hidden = sum(1 for i in items if i["kind"] == "hidden")
                log.write(f"{stamp},{url},ok,{len(items)},{n_hidden}\n")
                log.flush()
                print(f"{url}  items={len(items)} hidden={n_hidden}", flush=True)
                if done == 0:
                    queue += pick_links(page, page.url, int(pages_per_seed) - 1)
                done += 1
                time.sleep(INTERVAL)
        browser.close()
    log.close()


if __name__ == "__main__":
    main(*sys.argv[1:4])
