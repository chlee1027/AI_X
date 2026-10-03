"""저장한 원문 HTML 에서 ETC 신호를 훑는다 (렌더링 없이 바이트 수준).

출력: 파일별 title / meta description / JSON-LD 유무 / 제로폭 문자 수 / 외부 링크 도메인 상위 /
숫자 엔티티 수 / base64 덩어리 수 / ::before·::after content 규칙 수

사용: python scan_raw.py dir [glob]
"""
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

ZW = re.compile("[​‌‍⁠﻿᠎‪-‮]")
TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
META_DESC = re.compile(r"<meta[^>]+(?:name|property)=[\"'](?:description|og:description|og:title|keywords)[\"'][^>]*>", re.I)
LDJSON = re.compile(r"<script[^>]+application/ld\+json[^>]*>(.*?)</script>", re.S | re.I)
HREF = re.compile(r"href=[\"'](https?://[^\"']+)", re.I)
ENT = re.compile(r"&#(?:x[0-9a-fA-F]{2,6}|\d{3,7});")
B64 = re.compile(r"(?:atob\(|base64,)[\"']?([A-Za-z0-9+/=]{40,})")
PSEUDO = re.compile(r"::?(?:before|after)\s*\{[^}]*content\s*:\s*[\"'][^\"']{2,}", re.I)


def decode(b: bytes) -> str:
    for enc in ("utf-8", "cp949"):
        try:
            return b.decode(enc)
        except UnicodeDecodeError:
            pass
    return b.decode("utf-8", "replace")


def main(d: str, pattern: str = "*.html") -> None:
    for f in sorted(Path(d).glob(pattern)):
        t = decode(f.read_bytes())
        if len(t) < 1000:
            continue
        title = TITLE.search(t)
        hosts = Counter(urlsplit(u).hostname for u in HREF.findall(t))
        print(f"== {f.name}  ({len(t)} chars)")
        print("  title :", (title.group(1).strip()[:120] if title else None))
        for m in META_DESC.findall(t)[:4]:
            print("  meta  :", m[:200])
        print("  ld+json:", len(LDJSON.findall(t)), " zw:", len(ZW.findall(t)), " ent:", len(ENT.findall(t)),
              " b64:", len(B64.findall(t)), " pseudo-content:", len(PSEUDO.findall(t)))
        print("  hosts :", hosts.most_common(6))


if __name__ == "__main__":
    main(*sys.argv[1:])
