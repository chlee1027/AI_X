"""내려받은 CSS 파일에서 content 속성에 글자를 넣은 규칙을 모두 뽑는다 (css_content 실사례 찾기).

content 값을 CSS 이스케이프(\\cd5c 꼴)까지 풀어서 광고 어휘가 있는지 본다.
사용: python scan_css_content.py css_dir
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

AD = re.compile(r"카지노|바카라|토토|슬롯|홀덤|먹튀|비아그라|시알리스|대출|출장|안마|오피|텔레|카톡|도박|베팅|성인|\.com|\.net|\.top", re.I)
RULE = re.compile(r"([^{}]+)\{([^{}]*?content\s*:\s*([^;}]+)[^{}]*)\}", re.S)


def unesc(v: str) -> str:
    v = re.sub(r"\\([0-9a-fA-F]{1,6})\s?", lambda m: chr(int(m.group(1), 16)), v)
    return v.strip().strip("\"'")


def main(d: str) -> None:
    hangul, ad, n = [], [], 0
    for f in Path(d).glob("*_browser.html"):
        meta = json.loads(f.with_suffix(".json").read_text(encoding="utf-8"))
        t = f.read_bytes().decode("utf-8", "replace")
        if "<html" in t[:500].lower():
            continue
        n += 1
        for m in re.finditer(r"content\s*:\s*([^;}]{1,400})", t):
            val = m.group(1)
            start = max(t.rfind("}", 0, m.start()), t.rfind("{", 0, t.rfind("{", 0, m.start())))
            sel = t[start + 1: t.rfind("{", 0, m.start())]
            dv = unesc(val)
            if re.search(r"[가-힣]", dv) or AD.search(dv):
                row = (meta["url"], sel.strip()[-80:], dv[:120])
                (ad if AD.search(dv) else hangul).append(row)
    print("CSS 파일", n)
    print("광고 어휘 content", len(ad))
    for r in ad:
        print("  AD", r)
    print("한글 content", len(hangul), Counter(r[2] for r in hangul).most_common(30))


if __name__ == "__main__":
    main(sys.argv[1])
