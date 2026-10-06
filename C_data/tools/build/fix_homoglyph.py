"""사람 2 HOMOGLYPH 테스트셋 점검·수정 (2026-10-06, 역할 C).

사람 2 원본 폴더는 건드리지 않고 data/homoglyph 에 수정본을 쓴다. 원본은 미가림 번호가 있어 저장소 밖에 둔다.
1. 전화번호 가림: HG-RT-0041 (`010 – XXXX – XXXX`, 대시 앞뒤 공백 꼴이라 원 가림에서 빠짐)
2. 라벨 수정 5건: ㅋr톡 → hangul_lookalike, 토큰 전체가 수학 영숫자 → enclosed_alnum
3. 같은 문장 중복 4쌍에서 뒤 id 삭제 (검색결과 쪽 한 페이지에 검색어가 두 자리로 비친 3쌍, 목록 쪽 넘김 사이 같은 글 1쌍)
4. ypcd `????` 5건은 남기고 notes 에 원인 기록 (사이트 DB 가 4바이트 문자를 버림, 같은 캠페인이 hannam 에선 온전)
5. <출력 폴더>/add/add_*.yaml 을 끝에 이어 붙인다 (HG-RT-1778 …). 권장판에는 캠페인당 5건 상한 안에서만 넣는다.
사용: python tools/build/fix_homoglyph.py <사람 2 원본 폴더> data/homoglyph
"""
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

# 번호 숫자를 코드에 남기지 않도록 꼴로 찾아 가운데 자리만 0 으로 바꾼다
MASK = {"HG-RT-0041": re.compile(r"(010\s*[–-]\s*)\d{4}(\s*[–-]\s*\d{4})")}
RELABEL = {"HG-RT-0008": "hangul_lookalike", "HG-RT-1086": "hangul_lookalike",
           "HG-RT-0015": "enclosed_alnum", "HG-RT-0016": "enclosed_alnum", "HG-RT-0019": "enclosed_alnum"}
DROP = {"HG-RT-0014": "HG-RT-0010", "HG-RT-0016": "HG-RT-0015", "HG-RT-0018": "HG-RT-0017", "HG-RT-0881": "HG-RT-0876"}
BROKEN = {"HG-RT-0894", "HG-RT-0901", "HG-RT-0932", "HG-RT-1061", "HG-RT-1205"}
CAP = 5


def note(r, s):
    r["notes"] = (r["notes"] + " / " if r["notes"] else "") + s


def fix(rows):
    out = []
    for r in rows:
        rid = r["id"]
        if rid in DROP:
            continue
        if rid in MASK:
            pat = MASK[rid]
            assert pat.search(r["evidence_text"]) and pat.search(r["html"]), rid
            r["evidence_text"] = pat.sub(r"\g<1>0000\g<2>", r["evidence_text"])
            r["html"] = pat.sub(r"\g<1>0000\g<2>", r["html"])
            note(r, "2026-10-06 역할 C: 휴대폰 가운데 자리 가림(원 가림 누락)")
        if rid in RELABEL:
            note(r, f"2026-10-06 역할 C: subtype {r['subtype']} → {RELABEL[rid]}")
            r["subtype"] = RELABEL[rid]
        if rid in BROKEN:
            note(r, "일부 글자 ? = 사이트 DB 가 4바이트 문자를 버린 것(ypcd 478건 전부 4바이트 문자 0, 같은 캠페인이 hannam 에선 온전). 남은 위장 문자로 양성 유지")
        out.append(r)
    return out


def main(src: str, dst: str) -> None:
    src, dst = Path(src), Path(dst)
    full = fix(yaml.safe_load((src / "homoglyph_real_test.yaml").read_text(encoding="utf-8")))
    cap = fix(yaml.safe_load((src / "homoglyph_real_test_capped.yaml").read_text(encoding="utf-8")))
    n = 1778
    camp = Counter(r["campaign"] for r in cap)
    have = {re.sub(r"\s+", "", r["evidence_text"]) for r in full}
    for add in sorted((dst / "add").glob("add_*.yaml")):
        for r in yaml.safe_load(add.read_text(encoding="utf-8")) or []:
            k = re.sub(r"\s+", "", r["evidence_text"])
            if k in have:
                print("중복이라 뺌:", r["evidence_text"][:50])
                continue
            have.add(k)
            r["id"] = f"HG-RT-{n:04d}"
            n += 1
            full.append(r)
            if camp[r["campaign"]] < CAP:
                camp[r["campaign"]] += 1
                cap.append(dict(r))
    for name, rows in (("homoglyph_real_test.yaml", full), ("homoglyph_real_test_capped.yaml", cap)):
        (dst / name).write_text(yaml.safe_dump(rows, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
        print(name, len(rows), dict(Counter(r["subtype"] for r in rows)))


if __name__ == "__main__":
    main(*sys.argv[1:3])
