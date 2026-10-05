"""그누보드 댓글 수정용 숨김 사본(textarea#save_comment_N, display:none)을 가리키는 샘플을 보이는 댓글 요소로 바꾼다 (2026-10-06, 역할 C).

게시판 프로그램이 만든 숨김 사본은 업자가 숨긴 것이 아니고, 같은 글이 화면에는 article#c_N > p 로 보인다.
탐지기는 보이는 요소를 가리킬 것이므로 정답 위치도 그쪽이어야 한다.
- 원문(data/raw/etc/obf_all.json 의 url -> file)을 JS 끄고 네트워크 막은 채 띄워 article#c_N > p 의 outerHTML 을 얻는다
- 조각 html 의 textarea 를 그 p 로 바꾸고 expected_location 을 `#c_N > p` 로
- evidence 가 p 의 화면 글자에 그대로 있는지(공백만 무시) 확인. 없으면 멈춘다
사용: python tools/build/fix_hidden_copy_location.py data/samples/etc.yaml data/samples/combo_real.yaml
"""
import json
import re
import sys
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright

C = Path(__file__).resolve().parents[2]
TODAY = "2026-10-06"


def norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


def raw_file(url: str, byurl: dict) -> Path:
    f = byurl[url]
    rel = re.split(r"[\\/]data[\\/]raw[\\/]etc[\\/]", f)[-1]
    return C / "data" / "raw" / "etc" / rel


def main(*paths: str) -> None:
    byurl = {}
    for r in json.loads((C / "data/raw/etc/obf_all.json").read_text(encoding="utf-8")):
        byurl.setdefault(r["url"], r["file"])
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        ctx = b.new_context(java_script_enabled=False)
        ctx.route("**/*", lambda r: r.abort())
        pg = ctx.new_page()
        loaded = None
        for path in paths:
            rows = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
            n = 0
            for x in rows:
                m = re.fullmatch(r"textarea#save_comment_(\d+)", x["expected_location"])
                if not m:
                    continue
                cid = m.group(1)
                url = re.search(r"https?://\S+", x["source"]).group(0)
                f = raw_file(url, byurl)
                if loaded != f:
                    pg.set_content(f.read_text(encoding="utf-8", errors="replace"))
                    loaded = f
                el = pg.query_selector(f"article#c_{cid} > p")
                assert el, f"{x['id']}: article#c_{cid} > p 없음"
                outer, text = el.evaluate("e => e.outerHTML"), el.inner_text()
                assert norm(x["evidence_text"]) in norm(text), f"{x['id']}: evidence 가 보이는 댓글 글자에 없음"
                new_html, k = re.subn(rf'<textarea id="save_comment_{cid}"[^>]*>.*?</textarea>', lambda _: outer, x["html"], flags=re.S)
                assert k == 1, f"{x['id']}: 조각에서 textarea 를 못 찾음"
                old = x["expected_location"]
                x["html"], x["expected_location"] = new_html, f"#c_{cid} > p"
                x["notes"] = (x.get("notes") or "") + (f" / {TODAY}: 위치가 그누보드 댓글 수정용 숨김 사본({old}, display:none)을 가리켜, "
                                                       f"같은 글이 화면에 보이는 댓글 요소(#c_{cid} > p)로 바꿈. 원문 {f.name} 에서 다시 자름")
                n += 1
            Path(path).write_text(yaml.safe_dump(rows, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
            print(path, "바꿈", n)
        b.close()




def reselect_evidence(*paths: str) -> None:
    """2단계: 위치를 보이는 댓글(#c_N > p)로 바꾼 항목의 evidence 를 그 요소의 텍스트 노드 하나로 다시 고른다.

    숨김 textarea 안의 글은 줄바꿈으로 이어진 한 덩어리지만, 보이는 p 에서는 링크·<br> 로 텍스트 노드가 나뉜다.
    원래 evidence 와 가장 많이 겹치는 노드를 고르되,
      ETC zero_width: 보이지 않는 문자가 광고 문구 안에 있을 것(build_etc_found 의 기준)
      조합: 적어 둔 수법(techniques)이 그 노드에서 다시 다 잡힐 것(validate_combo 의 기준)
    을 만족하는 노드만 쓴다. 없으면 멈춘다.
    사용: python tools/build/fix_hidden_copy_location.py --evidence data/samples/etc.yaml data/samples/combo_real.yaml
    """
    sys.path.insert(0, str(C / "tools" / "build"))
    sys.path.insert(0, str(C / "tools" / "analyze"))
    import analyze_obf as A
    import build_etc_found as BEF
    from difflib import SequenceMatcher
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge")
        pg = b.new_page(java_script_enabled=False)
        for path in paths:
            rows = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
            n = 0
            for x in rows:
                if not re.fullmatch(r"#c_\d+ > p", x["expected_location"]):
                    continue
                pg.set_content(f"<!doctype html><html><body>{x['html']}</body></html>")
                nodes = pg.evaluate("s => [...document.querySelector(s).childNodes].filter(n => n.nodeType === 3).map(n => n.nodeValue.trim()).filter(Boolean)",
                                    x["expected_location"])
                if x["category"] == "ETC":
                    ok = [t for t in nodes if BEF.INVIS.search(t) and BEF.zw_meaningful(t)]
                else:
                    need = set(x["techniques"])
                    ok = [t for t in nodes if need <= set(A.features(t))]
                if not ok:
                    print(f"  {x['id']}: 조건에 맞는 텍스트 노드 없음 -> 건너뜀 (화면 요소에서는 이 수법 조합이 한 노드에 없다)")
                    continue
                ev = x["evidence_text"]
                best = max(ok, key=lambda t: SequenceMatcher(None, norm(ev), norm(t)).find_longest_match(0, len(norm(ev)), 0, len(norm(t))).size)
                if best != ev:
                    x["evidence_text"] = best
                    x["notes"] += (f" / {TODAY}: evidence 를 보이는 댓글의 텍스트 노드 그대로로 다시 고름"
                                   f"(숨김 사본에서는 여러 줄이 한 덩어리였음. 이전 앞부분: {ev[:40]!r})")
                    n += 1
            Path(path).write_text(yaml.safe_dump(rows, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
            print(path, "evidence 다시 고름", n)
        b.close()


if __name__ == "__main__":
    if sys.argv[1] == "--evidence":
        reselect_evidence(*sys.argv[2:])
    else:
        main(*sys.argv[1:])
