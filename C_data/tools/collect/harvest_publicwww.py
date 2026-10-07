"""PublicWWW(HTML 소스 검색)에서 숫자 엔티티로 쓴 도박 어휘가 든 페이지 주소를 모은다.

PublicWWW 는 ASCII 토큰만 검색하므로 한글 원문 대신 `&#52852;&#51648;&#45432;` 같은 엔티티 문자열로 찾는다.
무료 화면은 검색어마다 앞쪽 11곳 안팎만 주소를 보여 준다. 결과 페이지는 열지 않고 주소·조각만 저장한다
(본문 확인은 fetch_wayback.py 가 인터넷 아카이브 사본으로 한다).

사용: python tools/collect/harvest_publicwww.py                  (WORDS 의 엔티티 검색)
      python tools/collect/harvest_publicwww.py 이름 '검색어' ...   (검색어를 직접 주면 이름별 파일에 저장)
출력: data/raw/entity/publicwww_hits.json (직접 주면 publicwww_hits_<이름>.json)
"""
import json
import sys
import re
import urllib.parse
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

WORDS = ["카지노", "토토", "토토사이트", "카지노사이트", "온라인카지노", "먹튀", "먹튀검증", "바카라", "슬롯", "홀덤",
         "파워볼", "메이저사이트", "안전놀이터", "스포츠토토", "에볼루션", "사설토토", "바카라사이트", "슬롯사이트"]
OUT = Path(__file__).resolve().parents[2] / "data" / "raw" / "entity" / "publicwww_hits.json"


def ent(word):
    return "".join(f"&#{ord(c)};" for c in word)


def main(args):
    out = OUT if not args else OUT.with_name(f"publicwww_hits_{args[0]}.json")
    queries = [(w, f'"{ent(w)}"') for w in WORDS] if not args else [(q, q) for q in args[1:]]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    hits = []
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=False)  # 머리 없는 모드는 브라우저 확인 화면에서 멈춘다
        pg = b.new_page()
        for w, q in queries:
            pg.goto("https://publicwww.com/websites/" + urllib.parse.quote(q, safe="") + "/", timeout=60000)
            pg.wait_for_timeout(10000)
            body = pg.inner_text("body")
            total = re.search(r"([\d ]+) web pages", body)
            urls = pg.eval_on_selector_all(
                "a[href^='http']", "els => els.map(e => e.href).filter(h => !h.includes('publicwww.com'))")
            hits.append({"word": w, "query": q, "total": total.group(1).replace(" ", "") if total else None,
                         "urls": list(dict.fromkeys(urls)), "body": body,
                         "searched_at": datetime.now().isoformat(timespec="seconds")})
            print(w, hits[-1]["total"], len(hits[-1]["urls"]))
        b.close()
    out.write_text(json.dumps(hits, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1:])
