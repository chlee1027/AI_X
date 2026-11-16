"""1차 dev_data 양성 페이지 중 아직 안 연 페이지 -> seeds_r<k>.csv, 드라이버가 그 차례를 이어 받게 상태를 고친다.

앞 차례는 도메인당 최대 2쪽(seeds_dev)과 게시판 목록에서 고른 글만 열어서 안 연 양성 페이지가 남아 있다.
도메인당 PER 쪽, 업자 사이트로 보이는 도메인과 비중 큰 사이트는 뺀다. 사용: python make_seeds_devrest.py <k>
"""
import html
import json
import os
import random
import sys
from collections import Counter, defaultdict
from urllib.parse import urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_seeds_add import ROOT, already, is_excluded, reg, site_type_of  # noqa: E402
from round_driver import heavy_sites, write_seeds  # noqa: E402

PER = 40


def main():
    k = int(sys.argv[1])
    rng = random.Random(k)
    dev = json.load(open(os.path.join(ROOT, "logs", "dev_source_domains.json"), encoding="utf-8"))
    done = already()
    heavy = heavy_sites()
    by = defaultdict(set)
    excl = 0
    for host, items in dev.items():
        h = host.split(":")[0]
        if is_excluded(h):
            excl += 1
            continue
        if reg("http://" + h) in heavy:
            continue
        for u, p, _ in items:
            u = html.unescape(u)
            if p and u not in done and urlparse(u).scheme in ("http", "https"):
                by[h].add(u)
    rows = []
    for h, us in by.items():
        for u in rng.sample(sorted(us), min(PER, len(us))):
            rows.append(dict(page_url=u, site_type=site_type_of(h, urlparse(u).path), origin="dev_nongamble:rest"))
    rng.shuffle(rows)
    write_seeds(f"seeds_r{k}.csv", rows)
    sp = os.path.join(ROOT, "logs", "driver_state.json")
    st = json.load(open(sp, encoding="utf-8"))
    st.update(k=k, active=k, empty=0)
    json.dump(st, open(sp, "w", encoding="utf-8"), ensure_ascii=False)
    done_flag = os.path.join(ROOT, "logs", "driver_done")
    if os.path.exists(done_flag):
        os.remove(done_flag)
    print("남은 양성 페이지", sum(len(v) for v in by.values()), "씨앗", len(rows), "도메인", len(by), "뺀 도메인", excl, Counter(r["site_type"] for r in rows), "뺀 큰 사이트", sorted(heavy))


if __name__ == "__main__":
    main()
