"""원문 HTML 전체에서 엔티티·Base64·\\u 이스케이프로 감춘 광고를 찾는다 (렌더링 없이 원문만).

보는 자리
  b64_attr   : href·src·onclick·data-* 같은 속성 값이나 그 쿼리 파라미터 안의 Base64 (go.php?url=aHR0c...)
  b64_script : 스크립트 문자열 안의 Base64 (atob("..."), "data:text/html;base64,...")
  entity     : 숫자 엔티티가 3개 이상 이어진 것 (&#52852;&#51648;&#45432;)
  uescape    : \\uXXXX 가 3개 이상 이어진 것
디코딩 결과에 광고 어휘나 도박·의약품 도메인 꼴이 있어야 후보로 남긴다.
플랫폼 자동 생성(아임웹 설정 JSON 등)은 디코딩 결과가 { [ 로 시작하면 「json」 표시만 붙이고 남겨 둔다 (사람이 확인).

사용: python scan_encoding.py out.json dir [dir ...]
"""
import base64
import binascii
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import unquote

AD = re.compile(r"카지노|바카라|토토|슬롯|홀덤|먹튀|바둑이|꽁머니|비아그라|시알리스|레비트라|출장|안마|오피|조건만남|대출|내구제|"
                r"텔레|카톡|도박|베팅|배팅|casino|toto|baccarat|slot|bet\d|viagra|cialis", re.I)
B64 = re.compile(r"(?<![A-Za-z0-9+/=_-])([A-Za-z0-9+/_-]{16,}={0,2})(?![A-Za-z0-9+/=_-])")
ATTR = re.compile(r"""\b(href|src|action|onclick|data-[\w-]+|content|value)\s*=\s*(["'])(.*?)\2""", re.I | re.S)
ENT = re.compile(r"(?:&#(?:\d{2,6}|[xX][0-9a-fA-F]{2,5});\s*){3,}")
UESC = re.compile(r"(?:\\u[0-9a-fA-F]{4}){3,}")
SCRIPT = re.compile(r"<script\b[^>]*>(.*?)</script>", re.I | re.S)


def b64dec(s: str) -> str | None:
    s2 = s.replace("-", "+").replace("_", "/")
    s2 += "=" * (-len(s2) % 4)
    try:
        raw = base64.b64decode(s2, validate=True)
    except (binascii.Error, ValueError):
        return None
    try:
        t = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    # 사람이 읽을 글자가 대부분이어야 한다
    if sum(ch.isprintable() for ch in t) < 0.9 * len(t):
        return None
    return t


def main(out: str, dirs: list[str]) -> None:
    res, n = [], 0
    for d in dirs:
        for f in Path(d).glob("*_browser.html"):
            n += 1
            meta = f.with_suffix(".json")
            url = json.loads(meta.read_text(encoding="utf-8")).get("url", "") if meta.exists() else ""
            t = f.read_bytes().decode("utf-8", "replace")
            hits = []
            for name, _, val in ATTR.findall(t):
                v = html.unescape(unquote(val))
                for m in B64.finditer(v):
                    dec = b64dec(m.group(1))
                    if dec:
                        hits.append(("b64_attr", name, m.group(1), dec))
            for sc in SCRIPT.findall(t):
                for m in re.finditer(r"""["']([A-Za-z0-9+/=_-]{24,})["']|base64,([A-Za-z0-9+/=]{16,})""", sc):
                    s = m.group(1) or m.group(2)
                    dec = b64dec(s)
                    if dec:
                        hits.append(("b64_script", "script", s, dec))
                for m in UESC.finditer(sc):
                    hits.append(("uescape", "script", m.group(0), m.group(0).encode().decode("unicode_escape")))
            for m in ENT.finditer(t):
                hits.append(("entity", "html", m.group(0), html.unescape(m.group(0))))
            for kind, where, enc, dec in hits:
                if AD.search(dec) or re.search(r"[a-z0-9-]+\.(com|net|top|xyz|kr)\b", dec, re.I) and AD.search(enc + dec):
                    res.append({"file": str(f), "url": url, "kind": kind, "where": where, "enc": enc[:300], "dec": dec[:300],
                                "json": dec.lstrip().startswith(("{", "["))})
    # \u 디코딩에서 짝 없는 서로게이트가 나올 수 있어 그 글자만 바꿔 쓴다
    Path(out).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8", errors="replace")
    print("페이지", n, "후보", len(res))
    print(Counter((r["kind"], r["json"]) for r in res))
    print(Counter((r["kind"], r["url"].split("/")[2] if "//" in r["url"] else "") for r in res if not r["json"]).most_common(30))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
