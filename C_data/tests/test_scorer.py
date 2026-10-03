"""scorer.py 가 요강 붙임4 규칙대로 채점하는지 확인한다.

    python -m pytest tests/test_scorer.py -q
"""
import functools
import http.server
import json
import threading

import pytest

import scorer as S


def doc(findings, elapsed=100):
    return {"meta": {"topic": "TOPIC", "entry_url": "http://127.0.0.1/", "started_at": "2026-10-24T10:00:00+09:00",
                     "finished_at": "2026-10-24T10:01:40+09:00", "elapsed_sec": elapsed},
            "findings": findings}


def f(i, url, loc, tech, **kw):
    d = {"id": i, "url": url, "is_violation": True, "location": loc, "evidence_text": "x", "technique": tech}
    d.update(kw)
    return d


# ---------------------------------------------------------------- URL 규칙 (요강 예시 그대로)

@pytest.mark.parametrize("a,b,same", [
    ("https://www.example.go.kr/board/view?id=1024", "http://www.example.go.kr/board/view?id=1024", True),
    ("https://www.example.go.kr/board/list/", "https://www.example.go.kr/board/list", True),
    ("https://www.example.go.kr/board/list#top", "https://www.example.go.kr/board/list", True),
    ("https://x.go.kr/v?id=1024", "https://x.go.kr/v?id=1180", False),
    ("https://x.go.kr/v?id=1024&name=test", "https://x.go.kr/v?name=test&id=1024", True),
    ("http://127.0.0.1:8080/a", "http://127.0.0.1:8081/a", False),
    ("https://WWW.Example.go.kr/a", "https://www.example.go.kr/a", True),
])
def test_url_key(a, b, same):
    assert (S.url_key(a) == S.url_key(b)) is same


def test_split_frames_keeps_quoted():
    sel = 'iframe[src="https://www.example.go.kr/widget/notice"] >>> div.wrap > span.hidden-link'
    assert S.split_frames(sel) == ['iframe[src="https://www.example.go.kr/widget/notice"]', "div.wrap > span.hidden-link"]
    assert S.split_frames('a[title=">>>"] >>> b') == ['a[title=">>>"]', "b"]


def test_norm_selector_spacing():
    assert S.norm_selector("div.a>span") == S.norm_selector("div.a  >  span")


# ---------------------------------------------------------------- 채점 규칙 (문자열 방식)

U = "https://www.example.go.kr/board/view?id=1024"


def run(sub, ans, **kw):
    return S.score(doc(sub), doc(ans), S.StringResolver(), **kw)


def test_all_three_fields_must_match():
    ans = [f("a1", U, "div.a > span", "JAMO")]
    assert run([f("s1", U, "div.a > span", "JAMO")], ans)["correct"] == 1
    assert run([f("s1", U, "div.a > span", "HOMOGLYPH")], ans)["correct"] == 0
    assert run([f("s1", U.replace("1024", "1180"), "div.a > span", "JAMO")], ans)["correct"] == 0


def test_duplicates_merged():
    ans = [f("a1", U, "p", "JAMO")]
    r = run([f("s1", U, "p", "JAMO"), f("s2", U + "#x", "p", "JAMO")], ans)
    assert (r["submitted"], r["correct"], r["duplicates"], r["precision"]) == (1, 1, 1, 1.0)


def test_overlap_two_techniques_two_findings():
    ans = [f("a1", U, "p", "TRANSPARENT"), f("a2", U, "p", "OFFSCREEN")]
    r = run([f("s1", U, "p", "TRANSPARENT"), f("s2", U, "p", "OFFSCREEN")], ans)
    assert (r["correct"], r["recall"]) == (2, 1.0)


def test_schema_miss_wrong_vs_exclude():
    ans = [f("a1", U, "p", "JAMO")]
    bad = {"id": "s2", "url": U, "location": "q", "technique": "JAMO"}  # evidence_text·is_violation 없음
    sub = [f("s1", U, "p", "JAMO"), bad]
    assert run(sub, ans)["precision"] == 0.5
    assert run(sub, ans, schema_miss="exclude")["precision"] == 1.0


def test_technique_must_be_single_main_code():
    ans = [f("a1", U, "p", "JAMO")]
    r = run([f("s1", U, "p", ["JAMO", "HOMOGLYPH"]), f("s2", U, "p", "ETC")], ans)
    assert len(r["invalid"]) == 2 and r["correct"] == 0


def test_duplicate_id_is_invalid():
    ans = [f("a1", U, "p", "JAMO"), f("a2", U, "q", "JAMO")]
    r = run([f("s1", U, "p", "JAMO"), f("s1", U, "q", "JAMO")], ans)
    assert r["correct"] == 1 and len(r["invalid"]) == 1


def test_is_violation_false_counts_against():
    ans = [f("a1", U, "p", "JAMO")]
    r = run([f("s1", U, "p", "JAMO", is_violation=False)], ans)
    assert (r["submitted"], r["correct"]) == (1, 0)


def test_extra_matches_on_extra_finding():
    ans = [f("a1", U, "p", "ETC", extra_finding="ZERO_WIDTH")]
    sub = [{"id": "s1", "url": U, "location": "p", "evidence_text": "x", "technique": "ETC",
            "extra_finding": "ZERO_WIDTH"}]  # 요강 예시처럼 is_violation 없음
    assert run(sub, ans, extra=True)["correct"] == 1


def test_time_limit():
    r = S.score(doc([], elapsed=1801), doc([]), S.StringResolver())
    assert r["within_time_limit"] is False


def test_bom_and_broken_json_are_fatal(tmp_path):
    p = tmp_path / "r.json"
    p.write_bytes(b"\xef\xbb\xbf" + json.dumps(doc([])).encode())
    with pytest.raises(S.FatalSchema):
        S.load_result(p)
    p.write_text("{", encoding="utf-8")
    with pytest.raises(S.FatalSchema):
        S.load_result(p)
    p.write_text(json.dumps({"meta": {}}), encoding="utf-8")
    with pytest.raises(S.FatalSchema):
        S.load_result(p)


# ---------------------------------------------------------------- 같은 요소 판정 (브라우저)

PAGE = """<!doctype html><html><body>
<div class="board-list"><table><tr><td class="title"><a>정상</a></td></tr>
<tr><td class="title"><a>ｍｅｇａ－ＢＥＴ 첫충 30％ 지급</a></td></tr></table></div>
<div class="article-body"><p class="desc">안내 <span style="color:transparent">먹튀검증</span></p></div>
<span class="dup">a</span><span class="dup">b</span>
<iframe src="/widget/notice"></iframe>
</body></html>"""
WIDGET = '<!doctype html><div class="wrap"><span class="hidden-link" style="display:none">무료 슬롯</span></div>'


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    root = tmp_path_factory.mktemp("site")
    (root / "board").mkdir()
    (root / "board" / "view.html").write_text(PAGE, encoding="utf-8")
    (root / "widget").mkdir()
    (root / "widget" / "notice").write_text(WIDGET, encoding="utf-8")

    class H(http.server.SimpleHTTPRequestHandler):
        def guess_type(self, path):
            return "text/html; charset=utf-8"

        def log_message(self, *a):
            pass

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(H, directory=str(root)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()


@pytest.fixture(scope="module")
def dom():
    r = S.DomResolver(["127.0.0.1"])
    yield r
    r.close()


def test_dom_same_element_different_notation(site, dom):
    url = f"{site}/board/view.html"
    ans = [f("a1", url, "div.board-list > table > tbody > tr:nth-of-type(2) > td.title > a", "HOMOGLYPH")]
    sub = [f("s1", url, "tr:nth-child(2) a", "HOMOGLYPH")]
    assert S.score(doc(sub), doc(ans), dom)["correct"] == 1


def test_dom_ambiguous_selector_is_wrong(site, dom):
    url = f"{site}/board/view.html"
    ans = [f("a1", url, "span.dup:nth-of-type(1)", "OFFSCREEN")]
    r = S.score(doc([f("s1", url, "span.dup", "OFFSCREEN")]), doc(ans), dom)
    assert r["correct"] == 0 and r["fp"][0]["why"].startswith("multi")


def test_dom_iframe_path(site, dom):
    url = f"{site}/board/view.html"
    ans = [f("a1", url, f'iframe[src="{site}/widget/notice"] >>> div.wrap > span.hidden-link', "OFFSCREEN")]
    sub = [f("s1", url, "iframe >>> span.hidden-link", "OFFSCREEN")]
    assert S.score(doc(sub), doc(ans), dom)["correct"] == 1


def test_dom_wrong_element(site, dom):
    url = f"{site}/board/view.html"
    ans = [f("a1", url, "p.desc > span", "TRANSPARENT")]
    r = S.score(doc([f("s1", url, "p.desc", "TRANSPARENT")]), doc(ans), dom)
    assert (r["correct"], len(r["fn"])) == (0, 1)


def test_dom_refuses_other_hosts(dom):
    st, _ = dom.element("https://www.example.go.kr/board/view?id=1024", "p")
    assert st == "nopage"
