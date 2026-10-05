"""사람 3 OFFSCREEN 수정판에 visibility_hidden 원문 보충분 덧붙이기 (2026-10-06, 역할 C).

fix_offscreen.py 로 만든 수정판(93/93)은 그대로 두고 뒤에만 붙인다.
- 원문: add.yaml 의 항목을 OF-208 부터 번호를 매겨 offscreen_originals.yaml·json 에 붙임
- 시험용: 원문마다 Bootstrap `.invisible`(visibility:hidden) 규칙을 건 시험용 샘플을 만들어
  offscreen.yaml·json 에 붙이고 fixtures/ 에 HTML 을 만든다. 번호는 원문 다음(대조군 OF-101~107 과 안 겹치게)
- 시작.html: 삭제된 원문(상품명 가려짐) 행을 지우고 새 출처 표를 넣는다
YAML·JSON 은 원래 파일과 같은 형식(CRLF, YAML width=200, JSON indent=1)으로 다시 쓴다.
검증은 tools/validate/check_offscreen.py 로 따로 돌린다.
사용: python tools/build/add_offscreen.py data/offscreen add.yaml "출처 이름"
"""
import html as H
import json
import re
import sys
from pathlib import Path

import yaml

TODAY = "2026-10-06"
DELETED = ["OF-161", "OF-162", "OF-163", "OF-164", "OF-166", "OF-167", "OF-168"]
RULE = ".invisible {\n  visibility: hidden;\n}"
# 기존 visibility_hidden 시험용과 같은 변형을 돌아가며 쓴다: 글자 요소에 class / 감싸는 요소에 class / 한 겹 더 감쌈
VARIANTS = [
    lambda i, t: f'<div class="review-root "><span id="{i}-text" class="invisible">{t}</span></div>',
    lambda i, t: f'<div class="review-root invisible"><span id="{i}-text">{t}</span></div>',
    lambda i, t: f'<div class="review-root invisible"><div><span id="{i}-text">{t}</span></div></div>',
]
FIXTURE = ('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
           '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'; img-src data:">'
           '<title>{id}</title><style>body{{margin:24px;font:16px/1.5 sans-serif;color:#111;background:#fff}}'
           '.review-root{{box-sizing:border-box;min-height:80px}}a{{color:#111}}{css}</style><body>{html}</body></html>')


def num(x: dict) -> int:
    return int(x["id"].split("-")[1])


def write_pair(base: Path, rows: list) -> None:
    base.with_suffix(".yaml").write_bytes(yaml.safe_dump(rows, allow_unicode=True, sort_keys=False, width=200).replace("\n", "\r\n").encode("utf-8"))
    base.with_suffix(".json").write_bytes(json.dumps(rows, ensure_ascii=False, indent=1).replace("\n", "\r\n").encode("utf-8"))


def main(p3: str, add: str, title: str) -> None:
    p3 = Path(p3)
    orig_p, fixt_p = p3 / "data/originals/offscreen_originals", p3 / "data/samples/offscreen"
    orig = yaml.safe_load(orig_p.with_suffix(".yaml").read_text(encoding="utf-8"))
    fixt = yaml.safe_load(fixt_p.with_suffix(".yaml").read_text(encoding="utf-8"))
    ctrl = json.loads((p3 / "data/samples/offscreen_controls.json").read_text(encoding="utf-8"))
    new = yaml.safe_load(Path(add).read_text(encoding="utf-8"))
    have = {x["evidence_text"] for x in orig}
    assert not have & {x["evidence_text"] for x in new}, "이미 있는 문구"
    n = max(num(x) for x in orig + fixt + ctrl) + 1
    rows = []
    for x in new:
        x = dict(x, id=f"OF-{n:03d}")
        x["notes"] += f" / {TODAY}: visibility_hidden 보충(8 -> 15)으로 추가"
        orig.append(x)
        rows.append(x)
        n += 1
    for k, x in enumerate(rows):
        fid = f"OF-{n:03d}"
        t = H.escape(x["evidence_text"], quote=False)
        f = {"id": fid, "category": "OFFSCREEN", "subtype": "visibility_hidden", "html": VARIANTS[k % 3](fid, t), "css": RULE,
             "evidence_text": x["evidence_text"], "expected_location": f"#{fid}-text", "is_positive": True, "extra_finding": None,
             "source": x["source"],
             "notes": f"사용자가 승인한 원문 문구에 라이브러리 CSS 또는 명시한 파생 변형을 적용한 시험용 샘플. 실제 사이트 원문 HTML/CSS와 다름. "
                      f"/ {TODAY}: 원문 {x['id']} 문구에 Bootstrap .invisible(visibility:hidden) 규칙을 건 보충분"}
        fixt.append(f)
        (p3 / "fixtures" / f"{fid}.html").write_text(FIXTURE.format(id=fid, css=RULE, html=f["html"]), encoding="utf-8")
        x["_fixture"] = fid
        n += 1
    write_pair(orig_p, [{k: v for k, v in x.items() if k != "_fixture"} for x in orig])
    write_pair(fixt_p, fixt)
    # 시작.html
    page = p3 / "시작.html"
    s = page.read_text(encoding="utf-8")
    for i in DELETED:
        s = re.sub(rf"<tr><td>{i}</td>.*?</tr>\n", "", s)
    table = (f'<h2>{H.escape(title)}</h2><p><a href="{H.escape(rows[0]["source"])}">공개 원문 출처</a></p><table><thead><tr><th>원문 ID</th>'
             f'<th>광고 문구</th><th>원문 유형</th><th>시험용 화면</th></tr></thead><tbody>\n'
             + "".join(f'<tr><td>{x["id"]}</td><td>{H.escape(x["evidence_text"])}</td><td>visibility_hidden</td>'
                       f'<td><a href="fixtures/{x["_fixture"]}.html">{x["_fixture"]}</a></td></tr>\n' for x in rows)
             + "</tbody></table>")
    s = s.replace("</tbody></table><h2>가시 대조군</h2>", "</tbody></table>\n" + table + "<h2>가시 대조군</h2>", 1)
    s = re.sub(r"<p>검수 승인 102개 중 유형별 원문 100개, 참고 2개\.",
               f"<p>유형별 원문 {len(orig)}개(2026-10-05 역할 C 점검에서 상품명이 가려진 7개를 빼고 10-06 에 visibility_hidden 원문 7개를 보충), 참고 2개.", s)
    s = s.replace("시험용 CSS 샘플 100개와", f"시험용 CSS 샘플 {len(fixt)}개와")
    page.write_text(s, encoding="utf-8")
    print("원문", len(orig), [x["id"] for x in rows], "시험용", len(fixt), [x["_fixture"] for x in rows])


if __name__ == "__main__":
    main(*sys.argv[1:4])
