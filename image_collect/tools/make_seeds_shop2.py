"""쇼핑 씨앗 보충: 1차 목록은 robots·다른 주소 리디렉트로 20곳 중 6곳만 남았다(seeds_gen2.csv 19쪽).

리디렉트를 같은 등록 도메인 안에서만 3번까지 따라가고, 쇼핑 도메인을 더해 seeds_gen2.csv 에 덧붙인다. robots 는 그대로 지킨다.
"""
import csv
import os
import random
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from urllib.parse import urljoin, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_seeds_add import OPEN, PER_GEN, ROOT, SHOP_LINK, UA, already, anchors, reg, robots_ok  # noqa: E402

RETRY = ["oliveyoung.co.kr", "kurly.com", "interpark.com", "yes24.com"]
MORE = ["ssfshop.com", "lfmall.co.kr", "thehandsome.com", "a-bly.com", "nsmall.com", "homeplus.co.kr", "wemakeprice.com",
        "halfclub.com", "fashionplus.co.kr", "hnsmall.com", "shoppingntmall.com", "dongwonmall.com", "cjthemarket.com",
        "innisfree.com", "lge.co.kr", "himart.co.kr", "ktmall.com", "hfashionmall.com"]


def fetch_same(url, d):
    for _ in range(4):
        if not robots_ok(url):
            return "", "robots", url
        try:
            r = OPEN.open(urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ko"}), timeout=15)
            b = r.read(3_000_000)
            cs = r.headers.get_content_charset()
            time.sleep(1.0)
            for enc in [cs, "utf-8", "cp949"]:
                if enc:
                    try:
                        return b.decode(enc), "ok", url
                    except (UnicodeDecodeError, LookupError):
                        pass
            return b.decode("utf-8", "replace"), "ok", url
        except urllib.error.HTTPError as e:
            time.sleep(1.0)
            if e.code in (301, 302, 303, 307, 308) and e.headers.get("Location"):
                loc = urljoin(url, e.headers["Location"])
                if reg(loc) != d:
                    return "", f"offsite:{urlparse(loc).netloc}", url
                url = loc
                continue
            return "", f"http_{e.code}", url
        except Exception as e:
            time.sleep(1.0)
            return "", type(e).__name__, url
    return "", "too_many_redirects", url


def main():
    rng = random.Random(1)
    done = already()
    p = os.path.join(ROOT, "seeds_gen2.csv")
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    have = {r["page_url"] for r in rows}
    log = Counter()
    add = []
    for d in RETRY + MORE:
        page, st, final = fetch_same(f"https://www.{d}/", d)
        if not page and not st.startswith("offsite"):
            page, st, final = fetch_same(f"https://{d}/", d)
        log[st.split(":")[0]] += 1
        if not page:
            print(d, st, "skip", flush=True)
            continue
        links = sorted({u.split("#")[0] for u, _ in anchors(page, final) if reg(u) == d and SHOP_LINK.search(urlparse(u).path + "?" + urlparse(u).query)})
        links = [u for u in links if u not in done and u not in have and robots_ok(u)]
        pick = rng.sample(links, min(PER_GEN, len(links)))
        add += [dict(page_url=u, site_type="shopping", origin="gen2") for u in [final] + pick if u not in have]
        print(d, st, "final", final[:70], "links", len(links), flush=True)
    rows += add
    rng.shuffle(rows)
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["page_url", "site_type", "origin"])
        w.writeheader()
        w.writerows(rows)
    print(Counter(r["site_type"] for r in rows), log)


if __name__ == "__main__":
    main()
