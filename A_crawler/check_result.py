"""결과 파일 형식 검사(브라우저 없이). 요강 형식: UTF-8(BOM 없음), 최상위 meta·findings, finding 필수 칸과 타입,
4종 코드, result_extra 는 technique=ETC + extra_finding. 팀 채점기(scorer.py)의 형식 검사와 같은 기준이다.

  python check_result.py <결과 폴더>      # result.json, result_extra.json 을 본다. 문제가 있으면 종료 코드 1
"""
import json
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

MAIN4 = ("HOMOGLYPH", "JAMO", "TRANSPARENT", "OFFSCREEN")
META_REQUIRED = {"topic": str, "entry_url": str, "started_at": str, "finished_at": str, "elapsed_sec": (int, float)}
FINDING_REQUIRED = {"id": str, "url": str, "is_violation": bool, "location": str, "evidence_text": str, "technique": str}
TIME_LIMIT_SEC = 30 * 60


def url_key(url):
    p = urlsplit(url.strip())
    return (p.netloc.lower(), p.path.rstrip("/"), tuple(sorted(parse_qsl(p.query, keep_blank_values=True))))


def check(path, extra):
    probs = []
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        return ["UTF-8 BOM 이 있다"], 0
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        return [f"JSON 파싱 불가: {e}"], 0
    if not isinstance(doc, dict) or "meta" not in doc or not isinstance(doc.get("findings"), list):
        return ["최상위에 meta 와 findings(배열)가 있어야 한다"], 0
    meta = doc["meta"]
    for k, t in META_REQUIRED.items():
        if k not in meta:
            probs.append(f"meta.{k} 없음")
        elif not isinstance(meta[k], t) or isinstance(meta[k], bool):
            probs.append(f"meta.{k} 타입 오류")
    for k in ("started_at", "finished_at"):
        try:
            datetime.fromisoformat(meta.get(k, ""))
        except (TypeError, ValueError):
            probs.append(f"meta.{k} 가 ISO 8601 이 아니다")
    if isinstance(meta.get("elapsed_sec"), (int, float)) and meta["elapsed_sec"] > TIME_LIMIT_SEC:
        probs.append(f"검출 시간 {meta['elapsed_sec']}초가 30분을 넘는다")
    ids, keys = Counter(), Counter()
    for n, f in enumerate(doc["findings"]):
        if not isinstance(f, dict):
            probs.append(f"findings[{n}] 객체 아님"); continue
        for k, t in FINDING_REQUIRED.items():
            if k == "is_violation" and extra and k not in f:
                continue
            if k not in f:
                probs.append(f"findings[{n}] {k} 없음")
            elif not isinstance(f[k], t):
                probs.append(f"findings[{n}] {k} 타입 오류")
        tech = f.get("technique")
        if extra:
            if tech != "ETC":
                probs.append(f"findings[{n}] technique 가 ETC 가 아니다: {tech!r}")
            if not f.get("extra_finding"):
                probs.append(f"findings[{n}] extra_finding 없음")
        elif tech not in MAIN4:
            probs.append(f"findings[{n}] technique 가 4종 코드가 아니다: {tech!r}")
        ids[f.get("id")] += 1
        keys[(url_key(str(f.get("url", ""))), f.get("location"), f.get("extra_finding") if extra else tech)] += 1
    probs += [f"id 중복: {i} ({c}번)" for i, c in ids.items() if c > 1]
    dup = sum(c - 1 for c in keys.values() if c > 1)
    if dup:
        probs.append(f"url·location·기법이 같은 항목 {dup}건(채점에서 1건으로 합쳐진다)")
    return probs, len(doc["findings"])


def main(folder):
    bad = False
    for name, extra in (("result.json", False), ("result_extra.json", True)):
        p = Path(folder) / name
        if not p.exists():
            print(f"{name}: 없음"); bad = True; continue
        probs, n = check(p, extra)
        print(f"{name}: 항목 {n}건, 문제 {len(probs)}건")
        for x in probs[:20]:
            print("  -", x)
        bad |= bool(probs)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "."))
