"""find_entity.py 후보에서 ETC encoding(숫자 엔티티) 샘플을 골라 data/samples/etc.yaml 끝에 덧붙인다.

고르는 규칙
  - 갈래 둘 다 넣는다: injected(나, 정상 페이지의 링크·본문 앵커) 는 사이트당 PER_INJ 개,
    takeover(가, 넘어간 도메인의 도박 홍보 페이지) 는 사이트당 PER_TAKE 개.
  - takeover 는 제목급(h1~h3) 하나와 본문급(p·li·a·span·td) 하나를 고르고, 둘 다 도박 어휘를 품고 1,500자 이하여야 한다.
  - 휴대폰 번호 꼴이 든 요소는 뺀다.
  - 지운 id 는 다시 쓰지 않는다: 지금 가장 큰 번호 다음부터 매긴다.
html 은 요소 원문(엔티티 그대로)에 바로 위 조상 MAX_ANC 개를 껍데기로 씌운 조각이다.

사용: python tools/build/add_etc_entity.py [--dry]
"""
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CANDS = ROOT / "data" / "raw" / "entity" / "entity_candidates.json"
ETC = ROOT / "data" / "samples" / "etc.yaml"
PER_INJ, PER_TAKE, MAX_ANC, MAX_LEN = 2, 2, 3, 1500
HEAD = {"h1", "h2", "h3"}
BODY = {"p", "li", "a", "span", "td", "strong", "b", "div"}
NON_KO_ENT = re.compile(r"&#(?:10[2-9]\d|11\d\d|12[0-7]\d|123[5-9]\d|124\d\d|125[0-3]\d|199\d\d|[2-3]\d{4}|40[0-8]\d\d);")  # 키릴(1024~1279)·가나(12352~12543)·한자(19968~40895) 엔티티


def sel_part(tag, attrs):
    part = tag
    if attrs.get("id") and re.fullmatch(r"[A-Za-z][\w-]*", attrs["id"]):
        return part + "#" + attrs["id"]
    for c in (attrs.get("class") or "").split()[:3]:
        if re.fullmatch(r"-?[A-Za-z_][\w-]*", c):
            part += "." + c
    return part


def shell(tag, attrs):
    keep = {k: v for k, v in attrs.items() if k in ("id", "class") and v}
    a = "".join(f' {k}="{html.escape(v, quote=True)}"' for k, v in keep.items())
    return f"<{tag}{a}>", f"</{tag}>"


def build(c):
    anc = [x for x in c["chain_raw"] if x[0] not in ("html", "body")][-MAX_ANC:]
    opens, closes = zip(*[shell(t, a) for t, a in anc]) if anc else ((), ())
    snippet = "".join(opens) + c["outer"] + "".join(reversed(closes))
    loc = " > ".join([sel_part(t, a) for t, a in anc] + [sel_part(c["tag"], c["attrs"])])
    return snippet, loc


def host_ts(fname):
    m = re.match(r"(.+?)_(\d{14})\.html$", fname)
    return m.group(1), m.group(2)


def pick(cands):
    by = defaultdict(list)
    for c in cands:
        if c["phone"] or c["length"] > MAX_LEN:
            continue
        by[(c["file"], c["kind"])].append(c)
    chosen = []
    for (f, kind), cs in sorted(by.items()):
        if kind == "injected":
            chosen += cs[:PER_INJ]
            continue
        in_head = lambda c: c["tag"] in HEAD or any(t in HEAD for t, _ in c["chain_raw"])
        heads = [c for c in cs if in_head(c)]
        bodies = [c for c in cs if not in_head(c) and c["tag"] in BODY and len(c["decoded"]) >= 8]
        got = heads[:1] + bodies[:PER_TAKE - len(heads[:1])]
        chosen += got
    return chosen


def main(dry):
    cands = json.loads(CANDS.read_text(encoding="utf-8"))
    raw_cache = {}
    etc = yaml.safe_load(ETC.read_text(encoding="utf-8"))
    used = {x["evidence_text"] for x in etc}
    nxt = max(int(x["id"].split("-")[1]) for x in etc) + 1
    new = []
    for c in pick(cands):
        if c["evidence"] in used:
            continue
        used.add(c["evidence"])
        host, ts = host_ts(c["file"])
        url = f"https://{host}/"
        if c["file"] not in raw_cache:
            raw_cache[c["file"]] = (ROOT / "data/raw/entity/pages" / c["file"]).read_text(encoding="utf-8", errors="replace")
        other = bool(NON_KO_ENT.search(raw_cache[c["file"]]))
        snippet, loc = build(c)
        if c["kind"] == "takeover":
            why = (f"(가) 넘어간 도메인: 페이지 전체가 한국어 도박 홍보(제목 「{c['title'][:60]}」). "
                   "도박 페이지라 원 사이트는 열지 않고 인터넷 아카이브 사본만 봄")
        else:
            dest = re.sub(r"^https?://([^/]+).*$", r"\1", c["href"] or "") or "없음"
            why = (f"(나) 정상 제목 페이지(「{c['title'][:60]}」)의 링크 목록·본문에 심은 앵커. 목적지 {dest} 미방문")
        why += f". 디코딩: {c['decoded']}"
        if other:
            why += ". 같은 페이지가 한글 밖 문자도 엔티티로 내보낸다 = 일부러 숨긴 것이 아니라 사이트 출력 방식일 수 있음"
        new.append({
            "id": f"ET-{nxt:03d}", "category": "ETC", "subtype": "encoding", "html": snippet, "css": "",
            "evidence_text": c["evidence"], "expected_location": loc, "is_positive": True, "extra_finding": "ENCODING",
            "source": f"실측: {url} (Wayback 사본 https://web.archive.org/web/{ts}/{url} , 2026-10-07 수집, 원 사이트 미접속)",
            "notes": "숫자 엔티티 인코딩. " + why,
        })
        nxt += 1
    kinds = defaultdict(int)
    for n in new:
        kinds["takeover" if "(가)" in n["notes"] else "injected"] += 1
    print(len(new), dict(kinds), len({n["source"].split()[1] for n in new}), "sites")
    if dry:
        for n in new:
            print(n["id"], n["expected_location"][:80], "|", n["notes"][:100])
        return
    with ETC.open("a", encoding="utf-8") as f:
        f.write(yaml.safe_dump(new, allow_unicode=True, sort_keys=False, width=120))


if __name__ == "__main__":
    main("--dry" in sys.argv)
