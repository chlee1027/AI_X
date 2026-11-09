"""일반 이미지 3차 씨앗: 금융·병원·공공 사이트 첫 페이지와 같은 등록 도메인 링크 최대 4쪽 -> seeds_gen3.csv

목표 종류 중 finance, hospital 이 비어 있고 public 은 255장뿐이어서 더한다. robots 를 지키고, 리디렉트는 같은 등록 도메인 안에서만 따라간다.
"""
import csv
import os
import random
import sys
from collections import Counter
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_seeds_add import ROOT, already, anchors, reg, robots_ok  # noqa: E402
from make_seeds_shop2 import fetch_same  # noqa: E402

PER = 4
DOMS = {
    "finance": ["kbstar.com", "shinhan.com", "wooribank.com", "hanabank.com", "ibk.co.kr", "nonghyup.com", "kakaobank.com", "busanbank.co.kr",
                "dgb.co.kr", "samsungcard.com", "hyundaicard.com", "lottecard.co.kr", "samsunglife.com", "hanwhalife.com", "kbinsure.co.kr",
                "miraeasset.com", "samsungpop.com", "koreainvestment.com"],
    "hospital": ["snuh.org", "amc.seoul.kr", "samsunghospital.com", "severance.healthcare", "cmcseoul.or.kr", "kumc.or.kr", "ajoumc.or.kr",
                 "gilhospital.com", "hyumc.com", "dsmc.or.kr", "pnuh.or.kr", "knuh.kr", "cnuh.com", "chamc.co.kr", "eumc.ac.kr", "hallym.or.kr"],
    "public": ["seoul.go.kr", "busan.go.kr", "gg.go.kr", "incheon.go.kr", "daegu.go.kr", "gwangju.go.kr", "daejeon.go.kr", "mois.go.kr",
               "moe.go.kr", "mohw.go.kr", "motie.go.kr", "korea.kr", "nhis.or.kr", "kosis.kr"],
}


def main():
    import re
    bad = re.compile(r"login|logout|member|join|\.pdf$|\.hwp$|\.zip$|\.xlsx?$|download", re.I)
    rng = random.Random(3)
    done = already()
    rows, log = [], Counter()
    for kind, doms in DOMS.items():
        for d in doms:
            page, st, final = fetch_same(f"https://www.{d}/", d)
            if not page and not st.startswith("offsite"):
                page, st, final = fetch_same(f"https://{d}/", d)
            log[(kind, st.split(":")[0])] += 1
            if not page:
                print(kind, d, st, "skip", flush=True)
                continue
            links = sorted({u.split("#")[0] for u, _ in anchors(page, final)
                            if reg(u) == d and urlparse(u).scheme in ("http", "https") and len(urlparse(u).path) > 1 and not bad.search(u)})
            links = [u for u in links if u not in done and robots_ok(u)]
            pick = rng.sample(links, min(PER, len(links)))
            if final not in done:
                rows.append(dict(page_url=final, site_type=kind, origin="gen3"))
            rows += [dict(page_url=u, site_type=kind, origin="gen3") for u in pick]
            print(kind, d, st, "final", final[:60], "links", len(links), flush=True)
    rng.shuffle(rows)
    with open(os.path.join(ROOT, "seeds_gen3.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["page_url", "site_type", "origin"])
        w.writeheader()
        w.writerows(rows)
    print(Counter(r["site_type"] for r in rows), log)


if __name__ == "__main__":
    main()
