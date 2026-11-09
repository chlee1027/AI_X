"""1차 dev_data 의 출처 페이지 주소를 도메인별로 모은다 (수집 씨앗 목록용).

dev_data 만 읽는다(공모전 시험 몫은 건드리지 않는다).
출력: logs/dev_source_domains.json  {도메인: [[url, is_positive, 갈래], ...]}
"""
import collections
import glob
import json
import os
import re
from urllib.parse import urlparse

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
DEV = os.path.join(HERE, "..", "..", "v2_20261017", "dev_data")
OUT = os.path.join(HERE, "..", "logs", "dev_source_domains.json")


def items_of(d):
    if isinstance(d, list):
        return d
    if isinstance(d, dict):
        for v in d.values():
            if isinstance(v, list):
                return v
    return []


urls = []
for f in glob.glob(os.path.join(DEV, "*", "*.yaml")):
    kind = os.path.basename(os.path.dirname(f))
    for it in items_of(yaml.safe_load(open(f, encoding="utf-8"))):
        if not isinstance(it, dict):
            continue
        s = " ".join(str(it.get(k, "")) for k in ("source", "page_url", "url"))
        for m in re.findall(r"https?://[^\s'\"()]+", s):
            urls.append((m.rstrip(".,"), bool(it.get("is_positive")), kind))

dom = collections.defaultdict(list)
for u, p, c in urls:
    dom[urlparse(u).netloc.lower()].append((u, p, c))
pos = [d for d, v in dom.items() if any(p for _, p, _ in v)]
print("urls", len(urls), "domains", len(dom), "domains with positives", len(pos))
print(collections.Counter(d.rsplit(".", 1)[-1] for d in pos).most_common(15))
json.dump(dom, open(OUT, "w", encoding="utf-8"), ensure_ascii=False)
