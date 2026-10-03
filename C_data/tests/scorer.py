"""요강 붙임4 「평가 참고사항」을 재현하는 채점기.

    python tests/scorer.py 제출.json 정답.json [--resolve dom|string] [--extra] [--report out.json]

정답 파일은 제출과 같은 스키마(meta + findings)다. data/answers/ 나 mocksite 의 labels 를 그대로 넣는다.

요강에서 옮긴 규칙
  - 정답 = url · location · technique 셋이 모두 정답셋과 일치
  - url 비교: 끝 '/' 유무, http/https, '#' 이하는 무시. 쿼리 값이 다르면 다른 페이지, 항목 순서만 다르면 같은 페이지
  - location 비교: 문자열이 아니라 같은 요소를 가리키는가. 두 곳 이상을 가리키면 오답
  - url · location · technique 가 같은 제출이 여럿이면 1건으로 합친다
  - 파일 전체가 파싱 불가 -> 성능 0점

요강이 정하지 않아서 이 채점기가 정한 것 (보수적으로, 바꿀 수 있게)
  - 스키마 미준수 항목: 붙임2 는 「오답 처리」, 붙임4 는 「채점에서 제외」라 서로 다르다.
    기본은 오답(정밀도 분모에 넣음). --schema-miss exclude 로 바꾼다.
  - is_violation: false 인 항목: 제출 건수에는 넣고 정답으로는 치지 않는다.
  - UTF-8 BOM: 요강이 「BOM 없음」을 요구하므로 파일 전체 파싱 불가와 같이 0점으로 본다.
  - 점수 환산: 45점·35점의 환산식은 요강에 없다. 아래 「참고 점수」는 45 x 재현율, 35 x 정밀도로 둔 가정이다.
    검출 시간 20점은 다른 팀과의 상대 비교일 수 있어 30분 초과 여부만 판정한다.

location 확인 방식
  --resolve dom     (기본) 브라우저로 페이지를 열어 두 선택자가 같은 요소 하나를 가리키는지 본다.
                    iframe 은 'iframe[src="..."] >>> 선택자' 를 프레임별로 따라간다.
                    실제 사이트에 요청하지 않도록 --allow-host 에 적은 호스트(기본 127.0.0.1, localhost)만 연다.
  --resolve string  페이지 없이 선택자 문자열을 공백만 정리해 비교한다. 표기가 다르면 같은 요소라도 틀린다.
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

MAIN4 = ("HOMOGLYPH", "JAMO", "TRANSPARENT", "OFFSCREEN")
META_REQUIRED = {"topic": str, "entry_url": str, "started_at": str, "finished_at": str, "elapsed_sec": (int, float)}
FINDING_REQUIRED = {"id": str, "url": str, "is_violation": bool, "location": str,
                    "evidence_text": str, "technique": str}
TIME_LIMIT_SEC = 30 * 60


# ---------------------------------------------------------------- 파일 읽기와 스키마

class FatalSchema(Exception):
    """파일 전체가 채점 불가 (성능 0점)."""


def load_result(path):
    raw = Path(path).read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise FatalSchema("UTF-8 BOM 이 있다 (요강: BOM 없음)")
    try:
        doc = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        raise FatalSchema(f"JSON 파싱 불가: {e}")
    if not isinstance(doc, dict) or "meta" not in doc or "findings" not in doc:
        raise FatalSchema("최상위 객체에 meta 와 findings 가 모두 있어야 한다")
    if not isinstance(doc["findings"], list):
        raise FatalSchema("findings 는 배열이어야 한다")
    return doc


def meta_problems(meta):
    out = []
    if not isinstance(meta, dict):
        return ["meta 가 객체가 아니다"]
    for k, t in META_REQUIRED.items():
        if k not in meta:
            out.append(f"meta.{k} 없음")
        elif not isinstance(meta[k], t) or isinstance(meta[k], bool):
            out.append(f"meta.{k} 타입 오류")
    for k in ("started_at", "finished_at"):
        if isinstance(meta.get(k), str):
            try:
                datetime.fromisoformat(meta[k])
            except ValueError:
                out.append(f"meta.{k} 가 ISO 8601 이 아니다: {meta[k]}")
    if "tool_version" in meta and not isinstance(meta["tool_version"], str):
        out.append("meta.tool_version 타입 오류")
    return out


def finding_problems(f, extra):
    if not isinstance(f, dict):
        return ["객체가 아니다"]
    out = []
    for k, t in FINDING_REQUIRED.items():
        if k == "is_violation" and extra and k not in f:
            continue  # 요강의 result_extra 예시에는 is_violation 이 없다
        if k not in f:
            out.append(f"{k} 없음")
        elif not isinstance(f[k], t):
            out.append(f"{k} 타입 오류")
    tech = f.get("technique")
    if extra:
        if tech != "ETC":
            out.append(f"technique 가 ETC 가 아니다: {tech!r}")
        if not isinstance(f.get("extra_finding"), str) or not f.get("extra_finding"):
            out.append("extra_finding 없음")
    elif isinstance(tech, str) and tech not in MAIN4:
        out.append(f"technique 가 4종 코드가 아니다: {tech!r}")
    return out


# ---------------------------------------------------------------- URL · 선택자 정규화

def url_key(url):
    """요강의 URL 비교 규칙. scheme 무시, host 소문자(포트 유지), 끝 '/' 무시, '#' 무시, 쿼리는 순서 무시."""
    p = urlsplit(url.strip())
    path = p.path.rstrip("/")
    query = tuple(sorted(parse_qsl(p.query, keep_blank_values=True)))
    return (p.netloc.lower(), path, query)


def split_frames(selector):
    """'a >>> b >>> c' 를 따옴표 안의 '>>>' 는 건드리지 않고 나눈다."""
    parts, buf, quote, i = [], [], None, 0
    while i < len(selector):
        ch = selector[i]
        if quote:
            buf.append(ch)
            if ch == "\\" and i + 1 < len(selector):
                buf.append(selector[i + 1])
                i += 1
            elif ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            buf.append(ch)
        elif selector.startswith(">>>", i):
            parts.append("".join(buf).strip())
            buf = []
            i += 3
            continue
        else:
            buf.append(ch)
        i += 1
    parts.append("".join(buf).strip())
    return parts


def norm_selector(selector):
    """문자열 비교용: 결합자 앞뒤 공백을 한 칸으로, 연속 공백을 하나로."""
    out = []
    for part in split_frames(selector):
        part = re.sub(r"\s*([>+~])\s*", r" \1 ", part)
        out.append(re.sub(r"\s+", " ", part).strip())
    return " >>> ".join(out)


# ---------------------------------------------------------------- 요소 확인

class StringResolver:
    """페이지 없이 선택자 문자열로 요소를 대신한다."""

    def element(self, url, selector):
        return ("ok", norm_selector(selector))

    def close(self):
        pass


class DomResolver:
    """브라우저로 페이지를 열고 선택자를 요소 하나로 푼다. 같은 요소면 같은 표식을 돌려준다."""

    def __init__(self, allow_hosts, timeout_ms=15000):
        from playwright.sync_api import sync_playwright
        self.allow = {h.lower() for h in allow_hosts}
        self.timeout = timeout_ms
        self.pw = sync_playwright().start()
        try:
            self.browser = self.pw.chromium.launch(channel="msedge")
        except Exception:
            self.browser = self.pw.chromium.launch()
        self.pages = {}

    def _page(self, url):
        key = url_key(url)
        if key not in self.pages:
            host = (urlsplit(url).hostname or "").lower()
            if host not in self.allow:
                self.pages[key] = None
                print(f"  [건너뜀] 허용 목록에 없는 호스트라 열지 않는다: {url}", file=sys.stderr)
            else:
                page = self.browser.new_page()
                try:
                    page.goto(url, wait_until="load", timeout=self.timeout)
                    page.wait_for_timeout(300)
                except Exception as e:
                    print(f"  [열기 실패] {url}: {e}", file=sys.stderr)
                    page.close()
                    page = None
                self.pages[key] = page
        return self.pages[key]

    def element(self, url, selector):
        """('ok', 표식) | ('none'|'multi'|'nopage'|'bad', 설명)."""
        page = self._page(url)
        if page is None:
            return ("nopage", url)
        frame, path = page.main_frame, []
        parts = split_frames(selector)
        try:
            for depth, part in enumerate(parts):
                handles = self._query(frame, part, is_frame=depth < len(parts) - 1)
                if len(handles) == 0:
                    return ("none", part)
                if len(handles) > 1:
                    return ("multi", f"{part} -> {len(handles)}개")
                el = handles[0]
                if depth < len(parts) - 1:
                    child = el.content_frame()
                    if child is None:
                        return ("none", f"{part} 는 iframe 이 아니다")
                    path.append(self._index_in_frame(frame, el))
                    frame = child
                else:
                    path.append(self._index_in_frame(frame, el))
        except Exception as e:
            return ("bad", f"{selector}: {e}")
        return ("ok", tuple(path))

    SRC_ATTR = re.compile(r"""\[src=(["'])(.*?)\1\]$""")

    def _query(self, frame, part, is_frame):
        handles = frame.query_selector_all(part)
        m = self.SRC_ATTR.search(part) if is_frame else None
        if handles or not m:
            return handles
        # 요강: iframe src 가 상대 경로여도 절대 주소로 적는다. 속성값 대신 브라우저가 푼 주소(.src)로 비교한다.
        want = url_key(m.group(2))
        cands = frame.query_selector_all(part[:m.start()] or "iframe")
        return [h for h in cands if url_key(h.evaluate("e => e.src || ''")) == want]

    @staticmethod
    def _index_in_frame(frame, el):
        # 문서 순서상 위치 = 이 프레임 안에서 요소를 하나로 정하는 표식
        return frame.evaluate("e => Array.prototype.indexOf.call(document.getElementsByTagName('*'), e)", el)

    def close(self):
        self.browser.close()
        self.pw.stop()


# ---------------------------------------------------------------- 채점

def score(sub_doc, ans_doc, resolver, extra=False, schema_miss="wrong"):
    tech_of = (lambda f: f.get("extra_finding")) if extra else (lambda f: f.get("technique"))
    rep = {"meta_problems": meta_problems(sub_doc.get("meta")), "invalid": [], "not_violation": [],
           "unresolved": [], "answer_collisions": [], "duplicates": 0, "fp": [], "fn": []}

    # 정답 풀기
    answers = {}  # (urlkey, 기법, 요소표식) -> 정답 항목
    for a in ans_doc["findings"]:
        st, mark = resolver.element(a["url"], a["location"])
        if st != "ok":
            rep["unresolved"].append({"answer": a["id"], "why": f"{st}: {mark}"})
            continue
        key = (url_key(a["url"]), tech_of(a), mark)
        if key in answers:
            rep["answer_collisions"].append([answers[key]["id"], a["id"]])
        answers.setdefault(key, a)

    # 제출 풀기
    seen_ids, submitted, n_wrong_extra = set(), {}, 0
    for f in sub_doc["findings"]:
        probs = finding_problems(f, extra)
        fid = f.get("id") if isinstance(f, dict) else None
        if fid in seen_ids:
            probs.append(f"id 중복: {fid}")
        seen_ids.add(fid)
        if probs:
            rep["invalid"].append({"id": fid, "problems": probs})
            if schema_miss == "wrong":
                n_wrong_extra += 1
            continue
        st, mark = resolver.element(f["url"], f["location"])
        key = (url_key(f["url"]), tech_of(f), mark if st == "ok" else ("UNRESOLVED", f["location"]))
        if key in submitted:
            rep["duplicates"] += 1
            continue
        submitted[key] = (f, st, mark)

    correct, hit, by_tech = 0, set(), defaultdict(Counter)
    for key, (f, st, mark) in submitted.items():
        t = key[1]
        if f.get("is_violation") is False:
            rep["not_violation"].append(f["id"])
            by_tech[t]["fp"] += 1
            continue
        if st == "ok" and key in answers:
            correct += 1
            hit.add(key)
            by_tech[t]["tp"] += 1
        else:
            why = "정답에 없음" if st == "ok" else f"{st}: {mark}"
            rep["fp"].append({"id": f["id"], "url": f["url"], "location": f["location"],
                              "technique": t, "why": why})
            by_tech[t]["fp"] += 1
    for key, a in answers.items():
        if key not in hit:
            rep["fn"].append({"id": a["id"], "url": a["url"], "location": a["location"], "technique": key[1]})
            by_tech[key[1]]["fn"] += 1

    n_sub = len(submitted) + n_wrong_extra
    n_ans = len(answers)
    precision = correct / n_sub if n_sub else 0.0
    recall = correct / n_ans if n_ans else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    elapsed = (sub_doc.get("meta") or {}).get("elapsed_sec")
    rep.update({
        "answers": n_ans, "submitted": n_sub, "correct": correct,
        "precision": precision, "recall": recall, "f1": f1,
        "elapsed_sec": elapsed,
        "within_time_limit": isinstance(elapsed, (int, float)) and elapsed <= TIME_LIMIT_SEC,
        "ref_score_45_recall": 45 * recall, "ref_score_35_precision": 35 * precision,
        "by_technique": {t: dict(c) for t, c in sorted(by_tech.items(), key=lambda x: str(x[0]))},
    })
    return rep


def print_report(rep):
    print(f"정답 {rep['answers']} / 제출 {rep['submitted']} (중복 합침 {rep['duplicates']}) / 정답 검출 {rep['correct']}")
    print(f"정밀도 {rep['precision']:.4f}  재현율 {rep['recall']:.4f}  F1 {rep['f1']:.4f}")
    print(f"참고 점수(가정: 선형 환산) 정답 검출 개수 {rep['ref_score_45_recall']:.1f}/45 · "
          f"정답 추출 정확도 {rep['ref_score_35_precision']:.1f}/35")
    t = rep["elapsed_sec"]
    print(f"검출 시간 {t}초 — 30분 상한 {'안' if rep['within_time_limit'] else '초과 또는 값 없음 -> 20점 항목 0점'}")
    print("기법별 tp / fp / fn")
    for tech, c in rep["by_technique"].items():
        print(f"  {tech:<18} {c.get('tp', 0):>4} {c.get('fp', 0):>4} {c.get('fn', 0):>4}")
    if rep["meta_problems"]:
        print("meta 문제:", "; ".join(rep["meta_problems"]))
    if rep["invalid"]:
        print(f"스키마 미준수 항목 {len(rep['invalid'])}건 (예: {rep['invalid'][0]})")
    if rep["not_violation"]:
        print(f"is_violation=false 항목 {len(rep['not_violation'])}건 (제출 건수에 들어가고 정답으로 치지 않음)")
    if rep["answer_collisions"]:
        print(f"[경고] 정답 파일 안에서 url·location·technique 가 겹쳐 1건으로 합쳐진 정답 "
              f"{len(rep['answer_collisions'])}건 (예: {rep['answer_collisions'][0]}). "
              f"정답셋의 location 이 요소 하나를 가리키지 못한다는 뜻이다.")
    if rep["unresolved"]:
        print(f"정답 중 요소를 찾지 못해 뺀 것 {len(rep['unresolved'])}건 (예: {rep['unresolved'][0]})")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("submission")
    ap.add_argument("answer")
    ap.add_argument("--resolve", choices=["dom", "string"], default="dom")
    ap.add_argument("--allow-host", nargs="*", default=["127.0.0.1", "localhost"])
    ap.add_argument("--extra", action="store_true", help="result_extra.json 채점 (technique=ETC, extra_finding 으로 맞춘다)")
    ap.add_argument("--schema-miss", choices=["wrong", "exclude"], default="wrong")
    ap.add_argument("--report", help="상세 결과(FP·FN 목록 포함)를 JSON 으로 저장")
    a = ap.parse_args(argv)

    try:
        sub = load_result(a.submission)
    except FatalSchema as e:
        print(f"제출 파일 채점 불가 -> 성능 0점: {e}")
        return 2
    ans = load_result(a.answer)

    resolver = DomResolver(a.allow_host) if a.resolve == "dom" else StringResolver()
    try:
        rep = score(sub, ans, resolver, extra=a.extra, schema_miss=a.schema_miss)
    finally:
        resolver.close()
    print_report(rep)
    if a.report:
        Path(a.report).write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n",
                                  encoding="utf-8", newline="\n")
        print(f"상세 결과: {a.report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
