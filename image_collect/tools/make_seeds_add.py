"""추가 수집 씨앗 (2026-11-04): seeds_gen2.csv(뉴스·쇼핑 일반 이미지), seeds_nongamble.csv(도박 외 스팸 피해 페이지).

gen2: 도메인마다 첫 페이지 + 같은 등록 도메인의 기사·상품·분류 링크 최대 PER_GEN 쪽(시드 0 무작위). site_type 은 news/shopping 으로 고정.
nongamble: 피해 도메인의 스팸 글 페이지. 출처는 세 가지다.
  (1) 1차 dev_data 양성 항목 중 도박 외 낱말이 있는 페이지(logs/dev_nongamble.json)
  (2) 이미 연 페이지 글에 도박 외 낱말이 있던 도메인, 그 게시판 목록 1~3쪽에서 제목에 낱말이 있는 글(같은 등록 도메인만)
  (3) 검색으로 찾은 페이지 SEARCH (검색 도구가 일부 질의를 거절해 이것뿐이다)
도메인당 PER_NG 쪽. 업자 자신의 사이트로 보이는 도메인(이름 낱말·손으로 본 목록)은 빼고 logs/seeds_add_excluded.txt 에 남긴다.
목록 받기는 robots.txt 를 지키고 1초 쉬며 리디렉트를 따라가지 않는다. 글·링크 주소는 기록만 하고 다른 도메인은 열지 않는다.
"""
import csv
import glob
import html
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from urllib.parse import parse_qs, urljoin, urlparse

import tldextract

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_seeds_dev import MANUAL_EXCLUDE, OFFSITE_RE, VICTIM_SUFFIX, site_type_of  # noqa: E402
from dev_nongamble import KW  # noqa: E402
from robots_mini import Robots  # noqa: E402
import safe_io  # noqa: E402

ROOT = os.path.join(HERE, "..")
COL = os.path.join(ROOT, "collect")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
EX = tldextract.TLDExtract(suffix_list_urls=())
PER_GEN, PER_NG = 4, 6
NEWS = ["yna.co.kr", "hani.co.kr", "khan.co.kr", "donga.com", "joongang.co.kr", "mk.co.kr", "hankyung.com", "sedaily.com",
        "etnews.com", "zdnet.co.kr", "nocutnews.co.kr", "ohmynews.com", "ytn.co.kr", "newsis.com", "inews24.com", "pressian.com"]
SHOP = ["11st.co.kr", "gmarket.co.kr", "auction.co.kr", "ssg.com", "lotteon.com", "musinsa.com", "oliveyoung.co.kr", "kurly.com",
        "interpark.com", "hmall.com", "gsshop.com", "cjonstyle.com", "yes24.com", "kyobobook.co.kr", "aladin.co.kr", "danawa.com",
        "wconcept.co.kr", "29cm.co.kr", "ohou.se", "tmon.co.kr"]
NEWS_LINK = re.compile(r"/article|/arti/|/news/|articleView|/view/|/NewsView|\d{6,}", re.I)
SHOP_LINK = re.compile(r"product|goods|category|/item|display|/shop|/catalog|/best|/deal|/book", re.I)
DEALER = re.compile(r"viagra|cialis|loan|daechul|pharm|escort|massage|anma|opss", re.I)
MORE_EXCLUDE = {"web.archive.org", "indexrotator.com", "commu-test.com", "coinist.io", "phse365.com", "best-jubang.com",
                "www.best-jubang.com", "stackoverflow.com"}
SEARCH = ["https://www.theteams.kr/profile/207927/post/55479", "https://www.theteams.kr/profile/207093/post/55422",
          "https://www.theteams.kr/profile/207089/post/55455", "https://www.theteams.kr/profile/206413/post/55402",
          "https://www.theteams.kr/profile/206582/post/55413", "https://www.theteams.kr/profile/207376/post/55418"]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


OPEN = urllib.request.build_opener(NoRedirect)
ROB = {}


def reg(url):
    e = EX(url)
    return e.top_domain_under_public_suffix or urlparse(url).hostname or ""


def robots_ok(url):
    u = urlparse(url)
    key = f"{u.scheme}://{u.netloc}"
    if key not in ROB:
        try:
            body = urllib.request.urlopen(urllib.request.Request(key + "/robots.txt", headers={"User-Agent": UA}), timeout=10).read(500000)
            ROB[key] = Robots(body.decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            ROB[key] = Robots("User-agent: *\nDisallow: /") if 500 <= e.code < 600 else None
        except Exception:
            ROB[key] = None
    r = ROB[key]
    return True if r is None else r.can_fetch(url)


def fetch(url):
    """robots 를 지키고 리디렉트를 따라가지 않는다. 실패하면 빈 글."""
    if not robots_ok(url):
        return "", "robots"
    try:
        r = OPEN.open(urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ko"}), timeout=15)
        b = r.read(3_000_000)
        cs = r.headers.get_content_charset()
    except urllib.error.HTTPError as e:
        return "", f"http_{e.code}"
    except Exception as e:
        return "", type(e).__name__
    finally:
        time.sleep(1.0)
    for enc in [cs, "utf-8", "cp949"]:
        if enc:
            try:
                return b.decode(enc), "ok"
            except (UnicodeDecodeError, LookupError):
                pass
    return b.decode("utf-8", "replace"), "ok"


def anchors(page, base):
    for m in re.finditer(r"<a\s[^>]*?href=[\"']([^\"'#]+)[\"'][^>]*>(.*?)</a>", page, re.S | re.I):
        href = html.unescape(m.group(1).strip())
        if href.lower().startswith(("javascript:", "mailto:", "tel:")):
            continue
        txt = html.unescape(re.sub(r"<[^>]+>", " ", m.group(2)))
        try:
            yield urljoin(base, href), " ".join(txt.split())
        except ValueError:
            continue


def list_urls(url):
    """스팸 글 주소에서 그 게시판 목록 주소를 만든다. 모르는 형식이면 글 페이지 자체만(아래쪽에 목록이 붙는 게시판이 있다)."""
    u = urlparse(url)
    q = parse_qs(u.query)
    base = f"{u.scheme}://{u.netloc}"
    out = [url]
    if "bo_table" in q:
        out += [f"{base}{u.path}?bo_table={q['bo_table'][0]}&page={k}" for k in (1, 2, 3)]
    elif u.path.endswith("read.html") and "board_no" in q:
        out += [f"{base}{u.path[:-9]}list.html?board_no={q['board_no'][0]}&page={k}" for k in (1, 2, 3)]
    elif u.path.endswith("view.php") and "bdId" in q:
        out += [f"{base}{u.path[:-8]}list.php?bdId={q['bdId'][0]}&page={k}" for k in (1, 2, 3)]
    else:
        m = re.match(r"^/article/[^/]+/(\d+)/", u.path)
        if m:
            out += [f"{base}/board/product/list.html?board_no={m.group(1)}&page={k}" for k in (1, 2, 3)]
    return out


def is_excluded(host):
    h = (host or "").split(":")[0]
    if h in MANUAL_EXCLUDE or h in MORE_EXCLUDE or reg("http://" + h) in MORE_EXCLUDE:
        return True
    return bool((OFFSITE_RE.search(h) or DEALER.search(h)) and not VICTIM_SUFFIX.search(h))


def cat_of(text):
    for c, rx in KW.items():
        if rx.search(text):
            return c
    return ""


def already():
    done = set()
    for f in glob.glob(os.path.join(COL, "pages_*.csv")):
        done |= {r["page_url"] for r in safe_io.read_csv(f)}
    return done


def gen2():
    rng = random.Random(0)
    done = already()
    rows, log = [], []
    for kind, doms, rx in (("news", NEWS, NEWS_LINK), ("shopping", SHOP, SHOP_LINK)):
        for d in doms:
            home = f"https://www.{d}/"
            page, st = fetch(home)
            if not page:
                home = f"https://{d}/"
                page, st = fetch(home)
            log.append((kind, d, st))
            if not page:
                print(kind, d, st, "skip", flush=True)
                continue
            links = sorted({u.split("#")[0] for u, _ in anchors(page, home) if reg(u) == d and rx.search(urlparse(u).path + "?" + urlparse(u).query)})
            links = [u for u in links if u not in done and robots_ok(u)]
            pick = rng.sample(links, min(PER_GEN, len(links)))
            rows.append(dict(page_url=home, site_type=kind, origin="gen2"))
            rows += [dict(page_url=u, site_type=kind, origin="gen2") for u in pick]
            print(kind, d, st, "links", len(links), flush=True)
    rng.shuffle(rows)
    write("seeds_gen2.csv", rows)
    print(Counter(r["site_type"] for r in rows), Counter(s for _, _, s in log))


def nongamble():
    rng = random.Random(0)
    done = already()
    dev = json.load(open(os.path.join(ROOT, "logs", "dev_nongamble.json"), encoding="utf-8"))
    example = {}
    for f in glob.glob(os.path.join(COL, "pages_text_*.jsonl")):
        for line in open(f, encoding="utf-8"):
            r = json.loads(line)
            t = r["title"] + " " + r["text"]
            if any(len(rx.findall(t)) >= 2 for rx in KW.values()):
                example.setdefault(urlparse(r["page_url"]).hostname, []).append(r["page_url"])
    excl, by_host = set(), defaultdict(dict)
    for c, d in dev.items():
        for u in d:
            h = urlparse(u).hostname
            if is_excluded(h):
                excl.add(h)
            elif u not in done:
                by_host[h][u] = ("dev_nongamble", c)
                example.setdefault(h, []).append(u)
    log = []
    for h in sorted(example):
        if is_excluded(h):
            excl.add(h)
            continue
        lists = []
        for u in example[h][:3]:
            for x in list_urls(u):
                if x not in lists:
                    lists.append(x)
        found = 0
        for lu in lists[:6]:
            page, st = fetch(lu)
            log.append((h, lu[:100], st))
            for u, t in (anchors(page, lu) if page else ()):
                if reg(u) != reg("http://" + h) or u in done or u == lu or len(t) < 4:
                    continue
                c = cat_of(t)
                if c and u not in by_host[h] and robots_ok(u):
                    by_host[h][u] = ("board_list", c)
                    found += 1
        print(h, "lists", len(lists), "new posts", found, flush=True)
    rows = []
    for h, d in by_host.items():
        # 도메인당 PER_NG 쪽, 도박 외 종류가 고르게 들어가도록 종류별로 돌아가며 뽑는다
        cats = defaultdict(list)
        for u, (src, c) in sorted(d.items()):
            cats[c].append((u, src))
        for v in cats.values():
            rng.shuffle(v)
        pick = []
        while len(pick) < PER_NG and any(cats.values()):
            for c in sorted(cats):
                if cats[c] and len(pick) < PER_NG:
                    pick.append((c, *cats[c].pop()))
        for c, u, src in pick:
            rows.append(dict(page_url=u, site_type=site_type_of(h, urlparse(u).path), origin=f"{src}:{c}"))
    for u in SEARCH:
        if u not in done:
            rows.append(dict(page_url=u, site_type="community", origin="search_1104b:loan"))
    rng.shuffle(rows)
    write("seeds_nongamble.csv", rows)
    open(os.path.join(ROOT, "logs", "seeds_add_excluded.txt"), "w", encoding="utf-8").write("\n".join(sorted(excl)))
    print("seeds", len(rows), "hosts", len({urlparse(r["page_url"]).hostname for r in rows}), "excluded", len(excl), sorted(excl))
    print(Counter(r["origin"] for r in rows))
    print("fetch status", Counter(s for _, _, s in log))


def write(name, rows):
    with open(os.path.join(ROOT, name), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["page_url", "site_type", "origin"])
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    {"gen2": gen2, "nongamble": nongamble}[sys.argv[1]]()
