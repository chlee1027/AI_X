"""결과 파일이 모집요강 붙임4 스키마를 지키는지 점검 (10-21, 진행보고서 7-83절). 결과 폴더 하나를 받아 result.json·result_extra.json 을 본다.

점검 항목(요강 문장 기준):
  - 파일명 result.json / UTF-8, BOM 없음 / JSON
  - 최상위는 meta 와 findings 두 키, 검출 0건이어도 findings 는 []
  - meta: topic·entry_url·started_at·finished_at·elapsed_sec 필수(시각은 ISO 8601 + 시간대), tool_version 은 선택(문자열)
  - findings: id(문자열, 파일 안 중복 없음)·url(전체 URL)·is_violation(불리언)·location(문자열)·evidence_text(문자열)·technique 필수
  - technique: HOMOGLYPH·JAMO·TRANSPARENT·OFFSCREEN 중 하나(배열·여러 코드 불가). result_extra.json 은 "ETC" + extra_finding
  - (url, location, technique) 중복 없음
  - location: 「 > 」 앞뒤 공백 1칸, iframe 은 「iframe[src="절대 주소"] >>> 」, 속성값은 큰따옴표
  - elapsed_sec 이 30분(1,800초) 미만
사용: python 요강점검.py <결과 폴더> [<결과 폴더> ...]
"""
import json
import re
import sys
from pathlib import Path

TECH = {"HOMOGLYPH", "JAMO", "TRANSPARENT", "OFFSCREEN"}
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?([+-]\d{2}:\d{2}|Z)$")


def check(path, extra):
    errs = []
    if not path.exists():
        return [f"{path.name} 없음"]
    raw = path.read_bytes()
    if raw[:3] == b"\xef\xbb\xbf":
        errs.append("BOM 있음")
    try:
        d = json.loads(raw.decode("utf-8"))
    except Exception as e:
        return errs + [f"JSON/UTF-8 읽기 실패: {e}"]
    if not isinstance(d, dict) or set(d) != {"meta", "findings"}:
        errs.append(f"최상위 키가 meta·findings 둘이 아님: {list(d) if isinstance(d, dict) else type(d)}")
        return errs
    m = d["meta"]
    for k in ("topic", "entry_url", "started_at", "finished_at", "elapsed_sec"):
        if k not in m:
            errs.append(f"meta.{k} 없음")
    for k in ("topic", "entry_url", "started_at", "finished_at"):
        if k in m and not isinstance(m[k], str):
            errs.append(f"meta.{k} 문자열 아님")
    for k in ("started_at", "finished_at"):
        if isinstance(m.get(k), str) and not ISO.match(m[k]):
            errs.append(f"meta.{k} ISO 8601 아님: {m[k]}")
    if not isinstance(m.get("elapsed_sec"), (int, float)) or isinstance(m.get("elapsed_sec"), bool):
        errs.append("meta.elapsed_sec 숫자 아님")
    elif m["elapsed_sec"] >= 1800:
        errs.append(f"elapsed_sec {m['elapsed_sec']} >= 1800(30분)")
    if "tool_version" in m and not isinstance(m["tool_version"], str):
        errs.append("meta.tool_version 문자열 아님")
    fs = d["findings"]
    if not isinstance(fs, list):
        return errs + ["findings 배열 아님"]
    need = ["id", "url", "is_violation", "location", "evidence_text", "technique"] + (["extra_finding"] if extra else [])
    ids, keys = set(), set()
    for k, f in enumerate(fs):
        miss = [x for x in need if x not in f]
        if miss:
            errs.append(f"findings[{k}] 필드 없음 {miss}")
            continue
        for x in ("id", "url", "location", "evidence_text", "technique"):
            if not isinstance(f[x], str):
                errs.append(f"findings[{k}].{x} 문자열 아님")
        if not isinstance(f["is_violation"], bool):
            errs.append(f"findings[{k}].is_violation 불리언 아님")
        if f["id"] in ids:
            errs.append(f"id 중복 {f['id']}")
        ids.add(f["id"])
        if not re.match(r"^https?://", f["url"]):
            errs.append(f"findings[{k}].url 전체 URL 아님")
        if extra:
            if f["technique"] != "ETC":
                errs.append(f"findings[{k}] 추가 탐지인데 technique 이 ETC 아님")
            if not isinstance(f["extra_finding"], str) or not f["extra_finding"]:
                errs.append(f"findings[{k}].extra_finding 비었음")
        elif f["technique"] not in TECH:
            errs.append(f"findings[{k}].technique 4종 밖: {f['technique']}")
        key = (f["url"], f["location"], f["technique"], f.get("extra_finding"))
        if key in keys:
            errs.append(f"(url, location, technique) 중복: findings[{k}]")
        keys.add(key)
        loc = f["location"]
        if re.search(r"\S>|>\S", loc.replace(">>>", "")):
            errs.append(f"findings[{k}].location 「 > 」 앞뒤 공백 1칸 아님: {loc[:80]}")
        if ">>>" in loc:
            if not re.search(r"\S >>> \S", loc):
                errs.append(f"findings[{k}].location 「 >>> 」 공백 아님")
            for src in re.findall(r'iframe\[src="([^"]*)"\]', loc):
                if not re.match(r"^https?://", src):
                    errs.append(f"findings[{k}] iframe src 가 절대 주소 아님: {src[:80]}")
        if "'" in "".join(re.findall(r"\[[^\]]*\]", loc)):
            errs.append(f"findings[{k}].location 속성값이 큰따옴표가 아님")
    return errs


def main():
    bad = 0
    for d in sys.argv[1:]:
        for name, extra in (("result.json", False), ("result_extra.json", True)):
            e = check(Path(d) / name, extra)
            n = len(json.loads((Path(d) / name).read_text(encoding="utf-8"))["findings"]) if (Path(d) / name).exists() and not e[:1] == [f"{name} 없음"] else "-"
            print(f"{d} {name}: {'통과' if not e else '문제 ' + str(len(e))} (검출 {n})")
            for x in e[:10]:
                print("   ", x)
            bad += bool(e)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
