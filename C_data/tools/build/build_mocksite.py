"""실측 조각을 한 페이지에 하나씩 심어 페이지 단위 채점이 되는 모의 사이트를 만든다.

왜 필요한가
  지금 정답셋의 url 은 조각을 잘라 온 실제 페이지라, 한 페이지에서 여러 조각을 뜯어 오면
  (url + location + technique) 가 겹쳐 채점기 안에서 합쳐진다(799 -> 559). 조각마다 제 페이지를 주면
  url 이 달라져 겹치지 않는다. 실제 사이트에 요청하지 않도록 127.0.0.1 로만 연다.

무엇을 하나
  - 샘플(정답)마다 `site/<ID>.html` 한 장을 만든다. 조각(html)과 css 를 그대로 넣는다.
    meta_cloaking 은 조각을 <head> 에 넣고 본문은 평범한 글로 채운다(원래 검증기와 같은 꼴).
  - 각 페이지에 조각 하나만 있으니 원래 expected_location 이 그대로 유일 선택자가 된다.
  - to_answer.py 의 기법 판정을 그대로 불러, url 만 그 조각의 모의 페이지 주소로 바꾼 정답셋을 만든다.
    그래서 조각 단위 정답셋과 기법 구성·중복 제거(조합과 겹친 JAMO·HOMOGLYPH)가 똑같다.
  - 한 조합 조각에 기법이 여럿이면 같은 페이지·같은 선택자에 technique 만 다른 정답이 되어, 요강대로 따로 센다.

쓰는 법
  python tools/build/build_mocksite.py                  저장소 data(학습·검증) -> tests/mocksite/
  python tools/build/build_mocksite.py --data 봉인/data --out 봉인/mocksite   테스트 몫
  이어서 채점: (1) cd C_data 에서 모의 사이트 폴더를 http 로 연다
                 python -m http.server 8000 --directory tests/mocksite/site
               (2) python tests/scorer.py 제출.json tests/mocksite/answers/answer_result.json --resolve dom
  base url 기본은 http://127.0.0.1:8000/ 이고 --base 로 바꾼다(정답 url 과 서버 포트를 맞춰야 한다).
"""
import html as H
import json
import re
import sys
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import to_answer as ta  # noqa: E402


def arg(flag, default):
    return sys.argv[sys.argv.index(flag) + 1] if flag in sys.argv else default


DATA = Path(arg("--data", ta.DATA))
OUT = Path(arg("--out", HERE.parents[1] / "tests" / "mocksite"))
BASE = arg("--base", "http://127.0.0.1:8000/").rstrip("/") + "/"


def load_all():
    """id -> 샘플. to_answer 와 같은 파일을 읽는다."""
    files = {
        "decoy.yaml": DATA / "samples" / "decoy.yaml",
        "etc.yaml": DATA / "samples" / "etc.yaml",
        "combo_real.yaml": DATA / "samples" / "combo_real.yaml",
        "jamo.yaml": DATA / "samples" / "jamo.yaml",
        "offscreen": DATA / "offscreen" / "data" / "originals" / "offscreen_originals.yaml",
        "homoglyph": DATA / "homoglyph" / "homoglyph_real_test_capped.yaml",
    }
    by_id = {}
    for p in files.values():
        for it in yaml.safe_load(p.read_text(encoding="utf-8")) or []:
            by_id[it["id"]] = it
    return by_id


PAGE = """<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{css}</style>{head_extra}</head>
<body>
<header><nav>홈 &middot; 게시판 &middot; 공지 &middot; 문의</nav></header>
<main id="content">
{body}
</main>
<footer><small>모의 사이트 — 역할 C 평가용. 실제 사이트 아님.</small></footer>
</body></html>
"""


def page_html(it):
    css = it.get("css") or ""
    frag = it["html"]
    if it.get("subtype") == "meta_cloaking":
        # 조각이 <head> 안에 들어가는 꼴. 본문은 평범한 글로 채운다.
        body = "<article><h1>게시글</h1><p>요청하신 안내문입니다. 자세한 내용은 담당 부서로 문의해 주세요.</p></article>"
        head_extra = "\n" + frag
    else:
        body = f'<article><h1>게시글</h1>\n{frag}\n</article>'
        head_extra = ""
    return PAGE.format(title=H.escape(it["id"]), css=css, head_extra=head_extra, body=body)


def mock_url(sample_id):
    return f"{BASE}site/{sample_id}.html"


SUFFIX_RE = re.compile(r"_[A-Z][A-Z_]*$")  # 기법·추가유형은 대문자+밑줄. 샘플 id(HG-RT-0005 등)는 숫자로 끝난다


def remap(findings, key="url"):
    """finding id = '<sampleid>_<기법>' 에서 기법 접미사를 떼어 url 을 모의 페이지로 바꾼다. neg 는 id 가 샘플 id 그대로다."""
    out = []
    for f in findings:
        sid = SUFFIX_RE.sub("", f["id"])
        g = dict(f)
        g[key] = mock_url(sid)
        out.append((sid, g))
    return out


def main():
    by_id = load_all()
    # to_answer 의 조립을 그대로 쓴다. page_url 만 모의 주소로 바꾸면 되지만,
    # finding 의 id 에 샘플 id 가 들어 있으니 끝나고 url 만 바꾼다.
    saved_out = ta.OUT
    ta.OUT = OUT / "answers"  # to_answer 가 어디에 쓰든 상관없다. 우리가 다시 만든다.
    # to_answer.main 은 파일을 직접 쓰므로, 내부 조립만 복제한다.
    load = lambda n: yaml.safe_load((DATA / "samples" / n).read_text(encoding="utf-8"))  # noqa: E731
    decoy, etc, combo, jamo = load("decoy.yaml"), load("etc.yaml"), load("combo_real.yaml"), load("jamo.yaml")
    offscreen = yaml.safe_load((DATA / "offscreen/data/originals/offscreen_originals.yaml").read_text(encoding="utf-8"))
    homoglyph = yaml.safe_load((DATA / "homoglyph/homoglyph_real_test_capped.yaml").read_text(encoding="utf-8"))
    ta.OUT = saved_out

    norm = lambda t: re.sub(r"\s+", "", t)  # noqa: E731
    main4 = [ta.finding(i, code) for i in combo for code in i["label_codes"]]
    combo_jamo = {(ta.page_url(i), norm(i["evidence_text"])) for i in combo if "JAMO" in i["label_codes"]}
    # 같은 주소에서 evidence 가 조합 쪽 evidence 의 일부여도 같은 요소다(JM-069 는 CB-600 숨김 요소의 앞부분)
    jamo_dup = [i["id"] for i in jamo if any(u == ta.page_url(i) and norm(i["evidence_text"]) in e for u, e in combo_jamo)]
    main4 += [ta.finding(i, "JAMO") for i in jamo if i["is_positive"] and i["id"] not in jamo_dup]
    main4 += [ta.finding(i, "OFFSCREEN") for i in offscreen if i["is_positive"]]
    from urllib.parse import urlparse
    combo_hg = [((urlparse(ta.page_url(i)).hostname), norm(i["evidence_text"])) for i in combo if "HOMOGLYPH" in i["label_codes"]]
    hg_dup = [i["id"] for i in homoglyph
              if any(h == i["origin"]["host"] and (norm(i["evidence_text"]) in e or e in norm(i["evidence_text"]))
                     for h, e in combo_hg)]
    main4 += [ta.finding(i, "HOMOGLYPH") for i in homoglyph if i["is_positive"] and i["id"] not in hg_dup]
    extra = [ta.finding(i, "ETC", i["extra_finding"]) for i in etc]
    extra += [ta.finding(i, "ETC", name) for i in combo for name in i["extra_findings"]]
    neg = [{"id": i["id"], "url": ta.page_url(i), "location": i["expected_location"],
            "evidence_text": i["evidence_text"], "subtype": i["subtype"]} for i in decoy]

    main4_m, extra_m, neg_m = remap(main4), remap(extra), remap(neg)

    # 쓸 샘플 id = 정답·오탐에 쓰인 것
    used_ids = sorted({sid for sid, _ in main4_m + extra_m + neg_m})

    site = OUT / "site"
    answers = OUT / "answers"
    site.mkdir(parents=True, exist_ok=True)
    answers.mkdir(parents=True, exist_ok=True)

    missing = [sid for sid in used_ids if sid not in by_id]
    if missing:
        sys.exit(f"샘플을 못 찾음: {missing[:5]}")
    for sid in used_ids:
        (site / f"{sid}.html").write_text(page_html(by_id[sid]), encoding="utf-8", newline="\n")

    def doc(src, findings, key="findings"):
        return {"meta": {"topic": "mocksite", "kind": "answer", "base_url": BASE, "source": src}, key: [g for _, g in findings]}

    out = {
        "answer_result.json": doc(["mocksite"], main4_m),
        "answer_result_extra.json": doc(["mocksite"], extra_m),
        "negatives.json": doc(["mocksite"], neg_m, key="negatives"),
    }
    for name, d in out.items():
        (answers / name).write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    # 색인
    links = "\n".join(f'<li><a href="site/{sid}.html">{sid}</a> <small>{H.escape(by_id[sid]["category"])}/{H.escape(str(by_id[sid]["subtype"]))}</small></li>' for sid in used_ids)
    (OUT / "index.html").write_text(
        f"<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>모의 사이트 색인</title></head>"
        f"<body><h1>모의 사이트 — 역할 C 평가용 ({len(used_ids)}쪽)</h1><ul>{links}</ul></body></html>",
        encoding="utf-8", newline="\n")

    # 겹침 확인(0 이어야 한다)
    from collections import Counter
    # 채점기 키: 기본은 technique, --extra 는 extra_finding (scorer.score 의 tech_of 와 같다)
    for name, fs, tf in (("answer_result", main4_m, "technique"), ("answer_result_extra", extra_m, "extra_finding")):
        k = Counter((g["url"], g["location"], g.get(tf)) for _, g in fs)
        dup = sum(v - 1 for v in k.values() if v > 1)
        print(f"{name}.json  {len(fs)}건  (url+location+{tf}) 겹침 {dup}")
    print(f"negatives.json  {len(neg_m)}건")
    print(f"페이지 {len(used_ids)}장 -> {site}")
    print(f"정답 -> {answers}")


if __name__ == "__main__":
    main()
