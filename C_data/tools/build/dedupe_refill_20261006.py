"""ETC·조합 중복 정리와 채우기 (2026-10-06, 역할 C).

1. 조합: 사이트가 달라도 글이 같은 항목은 먼저 들어간 것만 남긴다(extend_combo.py 가 같은 사이트 안에서만 중복을 걸러 생긴 것).
   빈 자리는 combo_cand.yaml 에서 extend_combo 와 같은 규칙(BIG 이상 사이트 제외, 사이트당 새 항목 NEW_CAP 이하,
   도박 사이트 자체 제외)으로 채우되, 기존·ETC·JAMO 와 글이 같은 것(사이트 무관)과 숨김 사본(textarea) 위치는 뺀다.
2. ETC: 조합과 같은 요소(같은 페이지·선택자·글)인 항목은 조합 쪽을 남기고 ETC 에서 뺀다.
   (조합은 한 요소에 수법 2개 이상인 것이 정의상 들어갈 자리이고, ETC 는 대체 후보가 있다.)
   빈 자리는 같은 하위 유형 후보로 채운다. 후보: 200개로 줄일 때 덜어 낸 것(etc_pool) 다음에 원문 분석 결과(zw_cand).
   사이트당 상한(zero_width 10)을 지키고, 사이트를 돌아가며 고른다. 기존 ETC·조합·JAMO 와 글이 같은 것은 뺀다.
지운 id 는 다시 쓰지 않고 새 항목은 뒤 번호(ET-201~, CB-251~)로 붙인다.
3. (--drop) 지정한 조합 항목을 빼고 1 과 같은 규칙으로 채운다. 숨김 사본을 가리키던 조합 중 보이는 요소에서는
   적힌 수법들이 한 텍스트 노드에 함께 있지 않아 조합이 아니게 된 것을 뺄 때 쓴다.
사용: python tools/build/dedupe_refill_20261006.py etc_pool.yaml zw_cand.json
      python tools/build/dedupe_refill_20261006.py --drop CB-060,CB-063 "뺀 이유"
      python tools/build/dedupe_refill_20261006.py --drop-etc ET-086,ET-088 "뺀 이유" etc_pool.yaml zw_cand.json
4. (--drop-etc) 지정한 ETC 항목을 빼고 2 와 같은 규칙으로 같은 하위 유형을 채운다.
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

import yaml

C = Path(__file__).resolve().parents[2]
SAMPLES, RAW = C / "data" / "samples", C / "data" / "raw" / "etc"
TODAY = "2026-10-06"
sys.path.insert(0, str(C / "tools" / "build"))
import build_etc_found as BEF  # noqa: E402
import extend_combo as EC  # noqa: E402


def norm(s: str) -> str:
    return re.sub(r"[\s\W_]+", "", s).lower()


def host(x: dict) -> str:
    return re.sub(r"^(www|m|en)\.", "", urlsplit(re.search(r"https?://\S+", x["source"]).group(0)).netloc)


def load(name: str):
    return yaml.safe_load((SAMPLES / name).read_text(encoding="utf-8"))


def save(name: str, rows) -> None:
    (SAMPLES / name).write_text(yaml.safe_dump(rows, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")


def next_id(rows, prefix: str, start: int) -> int:
    return max([start - 1] + [int(x["id"].split("-")[1]) for x in rows]) + 1


def main(etc_pool: str, zw_cand: str) -> None:
    etc, combo, jamo = load("etc.yaml"), load("combo_real.yaml"), load("jamo.yaml")
    log = []

    # 1. 조합 중복
    seen, keep, drop = {}, [], []
    for x in combo:
        k = norm(x["evidence_text"])[:60]
        if k in seen:
            drop.append((x["id"], seen[k]))
            continue
        seen[k] = x["id"]
        keep.append(x)
    log.append(f"조합 중복 삭제 {[d[0] for d in drop]} (같은 글: {[d[1] for d in drop]})")
    used = {norm(x["evidence_text"])[:60] for x in combo + etc + jamo}
    per = Counter(host(x) for x in keep)
    cands = yaml.safe_load((RAW / "combo_cand.yaml").read_text(encoding="utf-8"))
    groups = defaultdict(list)
    for x in cands:
        h = host(x)
        k = norm(x["evidence_text"])[:60]
        if (k in used or per[h] >= 20 or h in EC.GAMBLING_SITES or "textarea" in x["expected_location"]
                or len(x.get("techniques", [])) < 2):
            continue
        used.add(k)
        groups[h].append(x)
    # 새 사이트(지금 0개)부터, 그다음 적은 사이트부터. 사이트당 하나씩
    order = sorted(groups, key=lambda h: (per[h], h))
    n = next_id(keep, "CB", 251)
    added_cb = []
    for h in order:
        if len(added_cb) >= len(drop):
            break
        x = groups[h][0]
        x["id"] = f"CB-{n:03d}"
        x["notes"] = (x.get("notes") or "") + f" / {TODAY}: 중복으로 뺀 {', '.join(d[0] for d in drop)} 자리를 채운 항목"
        n += 1
        added_cb.append(x)
    combo = keep + added_cb
    log.append(f"조합 추가 {[(x['id'], host(x), x['subtype']) for x in added_cb]}")

    # 2. ETC 와 조합의 같은 요소
    ckey = {(x["source"].split(" ")[1] if x["source"].startswith("실측:") else x["source"], x["expected_location"], norm(x["evidence_text"])) for x in combo}

    def ekey(x):
        return (x["source"].split(" ")[1] if x["source"].startswith("실측:") else x["source"], x["expected_location"], norm(x["evidence_text"]))
    gone = [x for x in etc if ekey(x) in ckey]
    etc = [x for x in etc if ekey(x) not in ckey]
    log.append(f"ETC 삭제(조합과 같은 요소) {[x['id'] for x in gone]}")
    need = Counter(x["subtype"] for x in gone)
    used = {norm(x["evidence_text"])[:60] for x in combo + etc + jamo}
    per = Counter((x["subtype"], host(x)) for x in etc)
    pool = yaml.safe_load(Path(etc_pool).read_text(encoding="utf-8"))
    for r in json.loads(Path(zw_cand).read_text(encoding="utf-8")):
        pool.append({"id": "", "category": "ETC", "subtype": "zero_width", "html": BEF.mask(r["snippet"]), "css": "",
                     "evidence_text": BEF.mask(r["ev"]), "expected_location": r["loc"], "is_positive": True, "extra_finding": "ZERO_WIDTH",
                     "source": f"실측: {r['url']} (2026-10-03 수집, JS 끄고 원문 렌더링)",
                     "notes": f"보이지 않는 문자 {', '.join(r.get('chars', []))} 가 광고 문구 안에 들어 있음"})
    n = next_id(etc + gone, "ET", 201)
    added_et = []
    for sub, k in need.items():
        got = 0
        while got < k:
            # 사이트를 돌아가며: 지금 그 하위 유형이 가장 적은 사이트의 후보부터
            ok = [x for x in pool if x["subtype"] == sub and norm(x["evidence_text"])[:60] not in used
                  and "textarea" not in x["expected_location"] and per[(sub, host(x))] < BEF.PER_HOST[sub]]
            if not ok:
                sys.exit(f"{sub} 후보 부족")
            x = min(ok, key=lambda c: (per[(sub, host(c))], pool.index(c)))
            used.add(norm(x["evidence_text"])[:60])
            per[(sub, host(x))] += 1
            x = dict(x, id=f"ET-{n:03d}")
            x["notes"] += f" / {TODAY}: 조합과 같은 요소라 뺀 {', '.join(g['id'] for g in gone)} 자리를 채운 항목"
            n += 1
            got += 1
            added_et.append(x)
    etc += added_et
    log.append(f"ETC 추가 {[(x['id'], host(x)) for x in added_et]}")
    save("etc.yaml", etc)
    save("combo_real.yaml", combo)
    print("\n".join(log))
    print("ETC", len(etc), Counter(x["subtype"] for x in etc), "| 조합", len(combo))


CAP = 6


def drop_refill(ids: str, reason: str) -> None:
    combo, etc, jamo = load("combo_real.yaml"), load("etc.yaml"), load("jamo.yaml")
    drop = set(ids.split(","))
    gone = [x for x in combo if x["id"] in drop]
    assert len(gone) == len(drop), "없는 id"
    keep = [x for x in combo if x["id"] not in drop]
    used = {norm(x["evidence_text"])[:60] for x in combo + etc + jamo}
    per = Counter(host(x) for x in keep)
    groups = defaultdict(list)
    for x in yaml.safe_load((RAW / "combo_cand.yaml").read_text(encoding="utf-8")):
        h, k = host(x), norm(x["evidence_text"])[:60]
        if (k in used or per[h] >= 20 or h in EC.GAMBLING_SITES or "textarea" in x["expected_location"]
                or len(x.get("techniques", [])) < 2):
            continue
        used.add(k)
        groups[h].append(x)
    n = next_id(combo, "CB", 251)
    added = []
    while len(added) < len(gone):
        # 10-04 덧붙임 상한은 사이트당 5. 남은 후보가 모두 이미 5개인 사이트에만 있어, 이번 채우기는 한 사이트에 하나씩만 넣어 6까지 허용
        order = sorted((h for h in groups if groups[h] and per[h] < CAP), key=lambda h: (per[h], h))
        if not order:
            sys.exit("조합 후보 부족")
        h = order[0]
        x = groups[h].pop(0)
        per[h] += 1
        x["id"] = f"CB-{n:03d}"
        x["notes"] = (x.get("notes") or "") + f" / {TODAY}: {reason} 뺀 {', '.join(sorted(drop))} 자리를 채운 항목"
        n += 1
        added.append(x)
    save("combo_real.yaml", keep + added)
    print("조합 삭제", sorted(drop), "| 추가", [(x["id"], host(x), x["subtype"]) for x in added], "| 합계", len(keep) + len(added))


def drop_refill_etc(ids: str, reason: str, etc_pool: str, zw_cand: str) -> None:
    etc, combo, jamo = load("etc.yaml"), load("combo_real.yaml"), load("jamo.yaml")
    drop = set(ids.split(","))
    gone = [x for x in etc if x["id"] in drop]
    assert len(gone) == len(drop), "없는 id"
    etc = [x for x in etc if x["id"] not in drop]
    used = {norm(x["evidence_text"])[:60] for x in combo + etc + jamo + gone}
    per = Counter((x["subtype"], host(x)) for x in etc)
    pool = yaml.safe_load(Path(etc_pool).read_text(encoding="utf-8"))
    for r in json.loads(Path(zw_cand).read_text(encoding="utf-8")):
        pool.append({"id": "", "category": "ETC", "subtype": "zero_width", "html": BEF.mask(r["snippet"]), "css": "",
                     "evidence_text": BEF.mask(r["ev"]), "expected_location": r["loc"], "is_positive": True, "extra_finding": "ZERO_WIDTH",
                     "source": f"실측: {r['url']} (2026-10-03 수집, JS 끄고 원문 렌더링)",
                     "notes": f"보이지 않는 문자 {', '.join(r.get('chars', []))} 가 광고 문구 안에 들어 있음"})
    n = next_id(etc + gone, "ET", 201)
    added, raised = [], set()
    for g in gone:
        sub = g["subtype"]
        ok = [x for x in pool if x["subtype"] == sub and norm(x["evidence_text"])[:60] not in used
              and "textarea" not in x["expected_location"] and per[(sub, host(x))] < BEF.PER_HOST[sub] + 1 and host(x) not in raised]
        if not ok:
            sys.exit(f"{sub} 후보 부족")
        x = min(ok, key=lambda c: (per[(sub, host(c))], pool.index(c)))
        if per[(sub, host(x))] >= BEF.PER_HOST[sub]:
            # 남은 후보가 모두 상한(zero_width 10)을 채운 사이트에만 있을 때: 한 사이트에 하나씩만 상한 + 1 허용
            raised.add(host(x))
        used.add(norm(x["evidence_text"])[:60])
        per[(sub, host(x))] += 1
        x = dict(x, id=f"ET-{n:03d}")
        x["notes"] += f" / {TODAY}: {reason} 뺀 {', '.join(sorted(drop))} 자리를 채운 항목"
        n += 1
        added.append(x)
    save("etc.yaml", etc + added)
    print("ETC 삭제", sorted(drop), "| 추가", [(x["id"], host(x)) for x in added], "| 합계", len(etc) + len(added))


if __name__ == "__main__":
    if sys.argv[1] == "--drop-etc":
        drop_refill_etc(*sys.argv[2:6])
    elif sys.argv[1] == "--drop":
        drop_refill(sys.argv[2], sys.argv[3])
    else:
        main(*sys.argv[1:3])
