"""추가 유형(result_extra.json) 채점 (10-20, 진행보고서 7-53절). 사용자가 직접 돌린다. 출력은 집계만(정답 내용·위치는 찍지 않는다).

정답 파일의 네 기법 밖(ETC 등) 정답과 우리 result_extra.json 을 맞춘다. 모집요강상 추가 유형은 정답 형식이 정해져 있지 않으므로 둘로 센다:
  - 위치 맞음      : url + 같은 요소(score_key 와 같은 판정)
  - 위치+유형 맞음 : 거기에 유형 이름까지 같음(정답 쪽 유형 이름 필드가 있을 때만. 이름 체계가 팀마다 다를 수 있어 참고로만)
정답 쪽 유형 이름 필드는 extra_finding·subtype·extra·name 순으로 찾고, 없으면 technique 값을 쓴다. 유형 이름별 개수도 찍는다(이름만, 내용 없음).
사용: python score_extra.py <result_extra.json> <정답 파일>   (samples 꼴·평평한 목록 꼴 모두)
"""
import json
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin, urlparse

from score_key import FIELD, TECH, resolve, split_loc, FAIL

KIND = ("extra_finding", "subtype", "extra", "name")


def kind_of(x, fallback):
    return str(next((x[k] for k in KIND if x.get(k)), fallback)).strip()


def etc_answers(raw, base):
    out = []
    if isinstance(raw, dict) and "samples" in raw:
        for s in raw["samples"]:
            if not s.get("label"):
                continue
            for f in s.get("findings") or []:
                if f.get("technique") not in TECH:
                    out.append({"url": urljoin(base, s.get("iframe_page") or s["url"]), "location": s["location"], "technique": "ETC",
                                "kind": kind_of(f, f.get("technique"))})
        return out
    items = raw
    if isinstance(raw, dict):
        lists = [v for v in raw.values() if isinstance(v, list)]
        items = raw.get("findings") or raw.get("answers") or (lists[0] if len(lists) == 1 else [])
    for x in items:
        y = {f: next((x[k] for k in ks if k in x), None) for f, ks in FIELD.items()}
        t = str(y["technique"]).strip()
        if any(t.upper() == c or t in al for c, al in TECH.items()):
            continue
        out.append({"url": urljoin(base, str(y["url"])), "location": y["location"], "technique": "ETC", "kind": kind_of(x, t)})
    return out


def main():
    from playwright.sync_api import sync_playwright
    res = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["findings"]
    raw = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    p0 = urlparse(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["meta"]["entry_url"])
    base = f"{p0.scheme}://{p0.netloc}/"
    ans = etc_answers(raw, base)
    ph = {urlparse(x["url"]).netloc for x in res} or {p0.netloc}
    ah = {urlparse(x["url"]).netloc for x in ans}
    if len(ph) == 1 and ah and not (ah & ph):  # score_key 와 같은 호스트 바꿔 맞추기(7-38절)
        h = next(iter(ph))
        for x in ans:
            x["url"] = urlparse(x["url"])._replace(scheme=p0.scheme, netloc=h).geturl()
        print(f"정답 주소 호스트를 검사한 사이트 호스트로 바꿔 채점합니다(정답 {len(ans)}개)")
    pred = [{"url": f["url"], "location": f["location"], "technique": "ETC", "kind": f.get("extra_finding", "")} for f in res]
    srt = lambda xs: sorted(xs, key=lambda x: split_loc(x["url"], x["location"])[0])  # noqa: E731
    ans, pred = srt(ans), srt(pred)
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg = b.new_page()
        cur = [None, False, pg]
        g = resolve(ans, pg, cur)
        q = resolve(pred, pg, cur)
        b.close()
    gk = {}
    for a, x in zip(ans, g):
        if x:
            gk.setdefault(x[:2], set()).add(a["kind"])
    print("정답 쪽 추가 유형(이름별 개수):", dict(Counter(a["kind"] for a in ans)), f"/ 풀린 것 {sum(1 for x in g if x)}")
    print("우리 예측(유형별 개수):", dict(Counter(a["kind"] for a in pred)), f"/ 풀린 것 {sum(1 for x in q if x)}")
    if FAIL:
        print("풀기 실패(종류별 개수):", dict(FAIL))
    loc_hit, both_hit, per = set(), set(), Counter()
    for a, x in zip(pred, q):
        if x and x[:2] in gk:
            loc_hit.add(x[:2])
            per[(a["kind"], "위치 맞음")] += 1
            if a["kind"] in gk[x[:2]]:
                both_hit.add((x[:2], a["kind"]))
        per[(a["kind"], "예측")] += 1
    n_g, n_p = len(gk), len({x[:2] for x in q if x}) + sum(1 for x in q if x is None)
    R, P = len(loc_hit) / max(n_g, 1), len(loc_hit) / max(n_p, 1)
    print(f"[위치 기준] 정답 요소 {n_g}, 예측 요소 {n_p}, 맞음 {len(loc_hit)} | 재현율 {R:.3f} 정밀도 {P:.3f}")
    print(f"[위치+유형 이름] 맞음 {len(both_hit)} (정답 유형 이름이 우리 이름과 같을 때만 셈)")
    for k in sorted({k for k, _ in per}):
        print(f"  {k:14s} 예측 {per[(k, '예측')]:3d}  위치 맞음 {per[(k, '위치 맞음')]:3d}")


if __name__ == "__main__":
    main()
