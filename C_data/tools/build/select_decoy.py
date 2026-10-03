"""DECOY 후보 -> decoy.yaml 100개.

a11y_sr_only 40 · hidden_menu 30 : 사이트를 돌아가며(round-robin) 고르고, a11y 는 숨김 기법(clip·1px·오프셋·text-indent·font-size)도 겹치지 않게 돌린다.
policy_text 15 · risky_word_normal 15 : 후보를 사람이 읽고 고른 번호 (아래 MANUAL).

사용: python select_decoy.py candidates.yaml[,candidates_r3.yaml] out_decoy.yaml
"""
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlsplit

import yaml

# 2026-10-03 후보 목록을 읽고 고른 번호 (candidates.yaml 순번)
MANUAL = {
    # 503 은 527 과 같은 법 조문 인용이라 507(포상금 안내)로 바꿨다
    "policy_text": [477, 478, 482, 484, 485, 492, 493, 507, 509, 512, 515, 520, 524, 527, 528,
                    # 2026-10-04 200개로 늘리며 추가: 조각(①·출처·첨부파일명)과 앞의 것과 같은 조문은 뺐다
                    479, 486, 488, 490, 491, 494, 496, 502, 506, 510, 513, 519, 525, 529, 531],
    "risky_word_normal": [571, 602, 553, 544, 543, 538, 546, 539, 533, 548, 577, 596, 585, 592, 540,
                          534, 535, 536, 542, 545, 547, 552, 560, 562, 569, 582, 586, 595, 604, 609],
}
QUOTA = {"a11y_sr_only": 80, "hidden_menu": 60}


def technique(reasons: list[str]) -> str:
    r = " ".join(reasons)
    for k, pat in [("clip", r"clip"), ("offset", r"offset"), ("text-indent", r"text-indent"),
                   ("font-size", r"font-size"), ("size1px", r"size:")]:
        if re.search(pat, r):
            return k
    return "display/visibility"


def host(c: dict) -> str:
    """기관 단위 도메인: www.easylaw.go.kr·easylaw.go.kr 를 같은 곳으로, spot.wooribank.com 은 wooribank.com 으로."""
    h = urlsplit(c["source"].split("|")[-1].strip()).netloc.lower()
    parts = h.split(".")
    keep = 3 if len(parts) >= 3 and parts[-2] in ("go", "or", "ac", "co", "re", "ne") and parts[-1] == "kr" else 2
    return ".".join(parts[-keep:])


SKIP_LINK = re.compile(r"(본문|메인메뉴|주메뉴|콘텐츠).{0,4}(바로가기|이동)|^본문으로")
MAX_SKIP_LINK = 6


def round_robin(cands: list[dict], n: int, by_tech: bool) -> list[dict]:
    groups = defaultdict(list)
    for c in sorted(cands, key=lambda c: len(c["html"])):
        if len(c["html"]) > 3000 or len(c["evidence_text"]) < 2:
            continue
        groups[host(c)].append(c)
    picked, used_tech, seen_pair = [], defaultdict(set), set()
    n_skip = 0
    while len(picked) < n and any(groups.values()):
        for h in sorted(groups):
            # 같은 문구+같은 규칙(같은 기관의 다른 페이지 반복)과 건너뛰기 링크 과다는 거른다
            while groups[h] and ((groups[h][0]["evidence_text"], groups[h][0]["css"]) in seen_pair or
                                 (SKIP_LINK.search(groups[h][0]["evidence_text"]) and n_skip >= MAX_SKIP_LINK)):
                groups[h].pop(0)
            if not groups[h] or len(picked) >= n:
                continue
            if by_tech:
                # 이 사이트에서 아직 안 쓴 기법을 먼저
                idx = next((i for i, c in enumerate(groups[h]) if technique(c["_hide_reasons"]) not in used_tech[h]), 0)
                c = groups[h].pop(idx)
                used_tech[h].add(technique(c["_hide_reasons"]))
            else:
                c = groups[h].pop(0)
            if SKIP_LINK.search(c["evidence_text"]):
                if n_skip >= MAX_SKIP_LINK:
                    continue
                n_skip += 1
            seen_pair.add((c["evidence_text"], c["css"]))
            picked.append(c)
    return picked


def main(cand_path: str, out: str) -> None:
    # 여러 후보 파일을 순서대로 이어 붙인다 (첫 파일의 순번이 MANUAL 번호라 바뀌지 않는다)
    cands = []
    for cp in cand_path.split(","):
        cands += yaml.safe_load(Path(cp).read_text(encoding="utf-8"))
    chosen = []
    for sub, n in QUOTA.items():
        chosen += round_robin([c for c in cands if c["subtype"] == sub], n, by_tech=(sub == "a11y_sr_only"))
    for sub, idxs in MANUAL.items():
        for i in idxs:
            assert cands[i]["subtype"] == sub, (i, cands[i]["subtype"])
            chosen.append(cands[i])
    items = []
    for k, c in enumerate(chosen, 1):
        sheets = ", ".join(s for s in c["_rule_sheets"] if s) or "없음(인라인 또는 규칙 불필요)"
        hidden = c["subtype"] in ("a11y_sr_only", "hidden_menu")
        note = (f"실측 {c['_fetched_at'][:10]}. 숨김 원인 {', '.join(c['_hide_reasons'])} ({technique(c['_hide_reasons'])}). "
                if hidden else f"실측 {c['_fetched_at'][:10]}. 화면에 보이는 정상 본문. ")
        note += f"css 는 브라우저 CSSOM 직렬화 규칙(원 시트: {sheets}). 조각 렌더링으로 재현 확인"
        items.append({"id": f"DC-{k:03d}", "category": "DECOY", "subtype": c["subtype"], "html": c["html"],
                      "css": c["css"], "evidence_text": c["evidence_text"],
                      "expected_location": c["expected_location"], "is_positive": False, "extra_finding": None,
                      "source": c["source"], "notes": note})
    Path(out).write_text(yaml.safe_dump(items, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
    from collections import Counter
    print(Counter(i["subtype"] for i in items))
    print("사이트 수:", len({host(c) for c in chosen}))
    print("a11y 기법:", Counter(technique(c["_hide_reasons"]) for c in chosen if c["subtype"] == "a11y_sr_only"))


if __name__ == "__main__":
    main(*sys.argv[1:3])
