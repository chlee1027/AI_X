"""정답 파일(answer.json)로 result.json 을 요강 붙임4 방식으로 채점한다. 팀원 사이트·블라인드 사이트용.

정답 파일 형식: [{"url": "...", "location": "CSS 선택자", "technique": "OFFSCREEN"}, ...]  (result.json 의 findings 와 같은 필드)
  {"findings": [...]} 처럼 감싼 꼴, selector·type 같은 다른 필드 이름, 한글 기법 이름도 받는다(load_answer).
  못 읽으면 값은 빼고 구조(키 이름·자료형)만 알려 준다.
판정: url(끝 / 유무, http/https, # 뒤 무시, 쿼리 순서 무시) + 같은 요소 + 기법이 모두 같으면 정답.
  같은 요소 = 두 선택자를 실제 페이지에서 풀어 같은 요소를 가리키는지로 본다. 두 곳 이상을 가리키면 오답.
  iframe 안 요소는 `iframe[src="주소"] >>> 선택자` 를 그 주소의 문서에서 푼다(정답 쪽이 iframe 문서 주소를 url 로 적어도 같게 본다).
출력은 집계만(기본). --detail 을 주면 맞음·놓침·오탐 목록을 낸다(정답 내용을 보게 되므로 블라인드 채점에서는 쓰지 않는다).

사용: python score_key.py <result.json> <answer.json> [--detail]
"""
import json
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse, parse_qsl, urljoin

JS = """(s) => { try { const m = document.querySelectorAll(s); if (m.length !== 1) return null;
  return Array.prototype.indexOf.call(document.getElementsByTagName('*'), m[0]); } catch (e) { return null; } }"""


def nurl(u):
    p = urlparse(u)
    path = p.path.rstrip("/").removesuffix(".html").removesuffix("/index")  # Netlify 는 .html 없는 주소로도 같은 문서를 준다
    return (p.netloc.lower().removeprefix("www."), path, tuple(sorted(parse_qsl(p.query))))


def split_loc(url, loc):
    """-> (문서 주소, 문서 안 선택자). iframe 은 마지막 >>> 앞의 src 문서(상대 주소면 바깥 문서 기준으로 푼다)."""
    parts = [x.strip() for x in loc.split(">>>")]
    doc = url
    for fr in parts[:-1]:
        src = fr[fr.find('src="') + 5: fr.rfind('"')]
        doc = urljoin(doc, src)
    return doc, parts[-1]


FAIL = Counter()  # 10-19(7-38절): 못 연 문서·못 푼 선택자를 오류 종류별로 센다(주소는 찍지 않는다)


def resolve(items, pg, cur):
    """items 는 문서 주소 순으로 정렬돼 있어야 한다. cur = [지금 열린 문서, 열기 성공 여부, 페이지].
    10-19(7-38절): 한 문서를 열다 페이지가 망가지면 그 뒤 문서가 모두 못 열려 「풀린 것 0」이 됐다 -> 실패하면 새 페이지로 바꾼다."""
    out = []
    for it in items:
        doc, sel = split_loc(it["url"], it["location"])
        if cur[0] != doc:
            try:
                cur[2].goto(doc, wait_until="load", timeout=20000)
                cur[:2] = [doc, True]
            except Exception as e:
                cur[:2] = [doc, False]
                FAIL[f"문서 못 엶: {type(e).__name__}"] += 1
                try:
                    cur[2].close()
                except Exception:
                    pass
                cur[2] = cur[2].context.browser.new_page()
        k = None
        if cur[1]:
            try:
                k = cur[2].evaluate(JS, sel)
            except Exception as e:
                FAIL[f"선택자 실행 오류: {type(e).__name__}"] += 1
        out.append(None if k is None else (nurl(doc), k, it["technique"]))
    return out


FIELD = {"url": ("url", "page", "page_url", "pageUrl", "href"),
         "location": ("location", "selector", "css", "css_selector", "cssSelector", "element", "loc"),
         "technique": ("technique", "type", "category", "tech", "method", "label")}
TECH = {"HOMOGLYPH": ("HOMOGLYPH", "유사문자", "동형문자", "유사 문자"), "JAMO": ("JAMO", "자모", "자모분리", "자모 분리"),
        "TRANSPARENT": ("TRANSPARENT", "투명", "투명색", "투명 글자"), "OFFSCREEN": ("OFFSCREEN", "화면밖", "화면 밖", "화면 밖 숨김")}


def shape(x, d=0):
    """값은 빼고 구조(자료형·키 이름·개수)만 문자열로. 정답 내용을 보지 않고 형식만 맞추기 위한 것."""
    if isinstance(x, dict):
        return "{" + ", ".join(f"{k}: {shape(v, d + 1) if d < 2 else type(v).__name__}" for k, v in x.items()) + "}"
    if isinstance(x, list):
        return f"list[{len(x)}] of " + (shape(x[0], d + 1) if x else "-")
    return type(x).__name__


def load_samples(raw, base):
    """팀원 사이트 꼴: {"meta", "samples": [{label, url(상대), location, iframe_page?, findings: [{technique}]}]}.
    label 참인 표본의 findings 마다 정답 1개(같은 location). 네 기법 밖(ETC 등)은 따로 센다.
    -> (정답 목록, 미끼 위치 목록, 네 기법 밖 정답 수)"""
    out, neg, other = [], [], Counter()
    for s in raw["samples"]:
        doc = urljoin(base, s.get("iframe_page") or s["url"])
        if not s["label"]:
            neg.append({"url": doc, "location": s["location"], "technique": None})
            continue
        for f in s["findings"]:
            if f["technique"] in TECH:
                out.append({"url": doc, "location": s["location"], "technique": f["technique"]})
            else:
                other[f["technique"]] += 1
    return out, neg, other


def load_answer(path):
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    items = raw
    if isinstance(raw, dict):  # {"findings": [...]} 처럼 한 번 감싼 꼴
        lists = [v for v in raw.values() if isinstance(v, list)]
        items = raw.get("findings") or raw.get("answers") or (lists[0] if len(lists) == 1 else None)
    if not isinstance(items, list) or not all(isinstance(x, dict) for x in items):
        sys.exit("정답 파일 형식을 못 읽었습니다. 구조만: " + shape(raw))
    out, bad = [], 0
    for x in items:
        y = {f: next((x[k] for k in ks if k in x), None) for f, ks in FIELD.items()}
        if None in y.values():
            sys.exit("정답 항목에 필요한 필드가 없습니다. 항목 구조만: " + shape(x))
        t = str(y["technique"]).strip()
        y["technique"] = next((c for c, al in TECH.items() if t.upper() == c or t in al), None)
        if y["technique"] is None:
            bad += 1
            continue
        out.append(y)
    if bad:
        print(f"경고: 기법 이름을 못 알아본 정답 {bad}개는 뺐습니다(기법 이름 목록: {sorted({str(x.get(k)) for x in items for k in FIELD['technique'] if k in x} - {a for al in TECH.values() for a in al})})")
    return out


def main():
    from playwright.sync_api import sync_playwright
    res = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["findings"]
    raw = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    neg, other = [], Counter()
    if isinstance(raw, dict) and "samples" in raw:
        p0 = urlparse(res[0]["url"]) if res else None
        base = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--base=")), f"{p0.scheme}://{p0.netloc}/" if p0 else "")
        ans, neg, other = load_samples(raw, base)
    else:
        ans = load_answer(sys.argv[2])
    # 10-19(7-38절): 정답을 다른 호스트(예: 팀원 로컬 서버 https://127.0.0.1:8443)로 적고 사이트는 배포 주소로 검사한 경우,
    # 정답과 예측의 호스트가 하나도 안 겹치고 예측 호스트가 하나뿐이면 정답 주소의 스킴·호스트를 예측 쪽으로 바꾼다(경로는 그대로).
    ph = {urlparse(x["url"]).netloc for x in res}
    ah = {urlparse(x["url"]).netloc for x in ans}
    if res and len(ph) == 1 and ah and not (ah & ph):
        p1 = urlparse(res[0]["url"])
        for x in ans:
            x["url"] = urlparse(x["url"])._replace(scheme=p1.scheme, netloc=p1.netloc).geturl()
        print(f"정답 주소의 호스트 {len(ah)}종이 검사한 사이트 호스트와 달라, 정답 {len(ans)}개의 호스트를 검사한 사이트 것으로 바꿔 채점합니다(경로는 그대로)")
    detail = "--detail" in sys.argv
    srt = lambda xs: sorted(xs, key=lambda x: split_loc(x["url"], x["location"])[0])  # noqa: E731
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg = b.new_page()
        cur = [None, False, pg]
        # 같은 문서를 한 번만 불러오도록 문서별로 묶어 푼다
        g = resolve(srt(ans), pg, cur)
        ng = resolve(srt(neg), pg, cur)
        q = resolve(srt(res), pg, cur)
        b.close()
    gold = {x for x in g if x}
    pred = {x for x in q if x}
    if neg or other:
        decoy = {x[:2] for x in ng if x}
        print(f"미끼(광고 아님) 표본 {len(neg)}개(풀린 것 {len(decoy)}) 중 우리 예측이 걸린 것 {sum(1 for x in pred if x[:2] in decoy)}개")
        print(f"네 기법 밖 정답(채점에서 뺌): {dict(other)}")
    if FAIL:
        print("풀기 실패(종류별 개수):", dict(FAIL))
    tp = gold & pred
    R = len(tp) / max(len(gold), 1)
    P = len(tp) / max(len(pred) + sum(1 for x in q if x is None), 1)
    print(f"정답 {len(ans)}개(풀린 것 {len(gold)}), 예측 {len(res)}개(풀린 것 {len(pred)}), 맞음 {len(tp)}")
    print(f"재현율 {R:.3f}  정밀도 {P:.3f}  점수 {(45 * R + 35 * P) / 80:.3f}")
    for t in ("HOMOGLYPH", "JAMO", "TRANSPARENT", "OFFSCREEN"):
        gt = {x for x in gold if x[2] == t}
        pt = {x for x in pred if x[2] == t}
        print(f"  {t:12s} 정답 {len(gt):3d}  예측 {len(pt):3d}  맞음 {len(gt & pt):3d}")
    # 10-21(진행보고서 7-88절): 기법 이름을 보지 않는 위치 기준과, 같은 요소에서 기법이 엇갈린 개수(집계만)
    ge, pe = {x[:2] for x in gold}, {x[:2] for x in pred}
    R2 = len(ge & pe) / max(len(ge), 1)
    P2 = len(ge & pe) / max(len(pe) + sum(1 for x in q if x is None), 1)
    print(f"[위치만] 정답 요소 {len(ge)}, 예측 요소 {len(pe)}, 맞음 {len(ge & pe)} | 재현율 {R2:.3f}  정밀도 {P2:.3f}  점수 {(45 * R2 + 35 * P2) / 80:.3f}")
    gt_by = {}
    for x in gold:
        gt_by.setdefault(x[:2], set()).add(x[2])
    mix = Counter()
    for x in pred - gold:
        if x[:2] in gt_by:
            mix[(x[2], "/".join(sorted(gt_by[x[:2]])))] += 1
    if mix:
        print("  같은 요소인데 기법이 엇갈림(우리 -> 정답):", {f"{a} -> {b}": n for (a, b), n in mix.most_common()})
    if detail:
        print(json.dumps({"놓침": sorted(map(str, gold - pred)), "오탐": sorted(map(str, pred - gold))}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
