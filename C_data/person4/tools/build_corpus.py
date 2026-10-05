"""받아 둔 공개 게시판 원문(HTML)에서 보이는 글자만 뽑아 한 파일로 모은다 (어휘·자모 근거 찾기용 색인).

- 입력: 역할 C 가 polite 모드로 받은 원문 폴더(data/raw/etc/r*/*_browser.html 와 짝 json)
- 스크립트·스타일·주석을 빼고 태그를 공백으로 바꾼 글자, 페이지 주소, 호스트를 줄 단위 JSON 으로 남긴다
- 도박 홍보 사이트 자체와 스팸 커뮤니티(출처로 쓰면 안 되는 곳)는 뺀다

사용: python build_corpus.py raw_etc_dir out.jsonl
"""
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

# 출처로 쓰지 않는 곳: 도박 홍보 사이트 자체, 토토 커뮤니티, 해외 스팸 집적 사이트
EXCLUDE = {"magino.co.kr", "ttcs-1.com", "www.goodreads.com", "goodreads.com"}


def text_of(raw: str) -> str:
    raw = re.sub(r"<script\b.*?</script>|<style\b.*?</style>|<!--.*?-->", " ", raw, flags=re.S | re.I)
    raw = re.sub(r"<br\s*/?>|</p>|</div>|</li>|</tr>|</h\d>", "\n", raw, flags=re.I)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    return re.sub(r"[ \t\r\f\v]+", " ", raw)


def main(src: str, out: str) -> None:
    n = 0
    with open(out, "w", encoding="utf-8") as w:
        for f in sorted(Path(src).glob("r*/*_browser.html")):
            j = f.with_suffix(".json")
            if f.stat().st_size < 1000 or not j.exists():
                continue
            meta = json.loads(j.read_text(encoding="utf-8"))
            url = meta.get("url", "")
            host = (urlsplit(url).hostname or "").lower()
            if host in EXCLUDE or host.removeprefix("www.") in EXCLUDE:
                continue
            t = text_of(f.read_bytes().decode("utf-8", "replace"))
            w.write(json.dumps({"url": url, "host": host, "fetched_at": meta.get("fetched_at", ""), "text": t},
                               ensure_ascii=False) + "\n")
            n += 1
    print("pages", n)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
