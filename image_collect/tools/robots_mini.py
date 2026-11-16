"""collect.py 의 Robots 판정과 같은 코드(모델을 불러오지 않고 쓰려고 뽑음)."""
import re
from urllib.parse import urlparse


class Robots:
    def __init__(self, text):
        self.rules, cur_any, in_rules = [], False, False
        for line in text.splitlines():
            line = line.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            k, v = (x.strip() for x in line.split(":", 1))
            k = k.lower()
            if k == "user-agent":
                if in_rules:
                    cur_any, in_rules = False, False
                cur_any = cur_any or v == "*"
            elif k in ("allow", "disallow"):
                in_rules = True
                if cur_any and v:
                    pat = re.escape(v).replace(r"\*", ".*")
                    if pat.endswith(r"\$"):
                        pat = pat[:-2] + "$"
                    self.rules.append((len(v), k == "allow", re.compile(pat)))

    def can_fetch(self, url):
        u = urlparse(url)
        path = (u.path or "/") + ("?" + u.query if u.query else "")
        hits = [(n, a) for n, a, p in self.rules if p.match(path)]
        return True if not hits else max(hits, key=lambda x: (x[0], x[1]))[1]
