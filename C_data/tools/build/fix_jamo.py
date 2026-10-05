"""jamo.yaml 점검 결과 고치기 (2026-10-05).

1. 전화번호 가림: 앞 세 자리(난독화 모양 포함)만 남기고 나머지 숫자·o·l 을 X 로. html·evidence_text 둘 다 같은 방식
2. 중복 제거: 공백을 뺀 evidence_text 가 같으면 앞의 것만 남김
3. 분류 바로잡기
   - 분해형이 「ㅋㅌ」(카톡 초성 축약)인 mixed_technique -> partial_mix. 겹친 다른 기법이 없다
   - 분해형이 「ㅣ」(자모를 구분자 | 대신 씀)인 것 -> 자모 분해가 아니라 닮은꼴 문자라 JAMO 에서 뺌
4. 덧붙일 항목(add.yaml, 선택)을 붙이고 subtype 순서로 정렬, id 를 JM-001 부터 다시 매김. 원래 id 는 notes 에 남김

사용: python fix_jamo.py jamo.yaml out.yaml [add.yaml]
"""
import html as H
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

PHONE = re.compile(r"(?<![\w])[0oOⓞ⓪０][\W_ㅡ]{0,3}[1lI①１][\W_ㅡ]{0,3}[016789oO０](?:[\W_ㅡ]{0,3}[\doOlI０-９①-⑨]){7,8}")
HEAD = re.compile(r"[0oOⓞ⓪０][\W_ㅡ]{0,3}[1lI①１][\W_ㅡ]{0,3}[016789oO０]")
ORDER = ["compat_full", "partial_mix", "conjoining_u1100", "mixed_technique"]


def mask(s: str) -> str:
    def one(m: re.Match) -> str:
        tok = m.group(0)
        keep = HEAD.match(tok).group(0)
        return keep + re.sub(r"[\doOlI０-９①-⑨]", "X", tok[len(keep):])
    return PHONE.sub(one, s)


def form(x: dict) -> str:
    m = re.search(r"→ (.+?);", x["notes"])
    return m.group(1) if m else ""


def main(src: str, out: str, add: str | None = None) -> None:
    xs = yaml.safe_load(Path(src).read_text(encoding="utf-8"))
    log = Counter()
    keep, seen = [], set()
    for x in xs:
        k = re.sub(r"\s+", "", x["evidence_text"])
        if k in seen:
            log["중복 제거"] += 1
            continue
        seen.add(k)
        if form(x) == "ㅣ":
            log["JAMO 아님(ㅣ 구분자) 제외"] += 1
            continue
        if x["subtype"] == "mixed_technique" and form(x) == "ㅋㅌ":
            x["subtype"] = "partial_mix"
            x["notes"] += " / 2026-10-05: 카톡 초성 축약(ㅋㅌ)뿐이라 겹친 다른 기법이 없어 mixed_technique -> partial_mix"
            log["ㅋㅌ -> partial_mix"] += 1
        new_html, new_ev = mask(x["html"]), mask(x["evidence_text"])
        if new_ev != x["evidence_text"]:
            x["notes"] += " / 2026-10-05: 전화번호 가림(앞 세 자리 모양만 남김)"
            log["전화번호 가림"] += 1
        x["html"], x["evidence_text"] = new_html, new_ev
        keep.append(x)
    if add:
        extra = yaml.safe_load(Path(add).read_text(encoding="utf-8")) or []
        for x in extra:
            k = re.sub(r"\s+", "", x["evidence_text"])
            if k not in seen:
                seen.add(k)
                keep.append(x)
                log["덧붙임"] += 1
    keep.sort(key=lambda x: ORDER.index(x["subtype"]))
    for i, x in enumerate(keep, 1):
        old = x["id"]
        new = f"JM-{i:03d}"
        if old != new and not str(old).startswith("NEW"):
            x["notes"] += f" / 이전 id {old}"
        x["id"] = new
        # html 은 evidence 를 감싼 span 래퍼뿐이라, 가린 evidence 로 다시 만든다 (html 쪽 &quot; 때문에 번호가 덜 가려지는 것 방지)
        x["html"] = f'<span id="jm-{i:03d}">' + H.escape(x["evidence_text"], quote=True) + "</span>"
        x["expected_location"] = f"#jm-{i:03d}"
    Path(out).write_text(yaml.safe_dump(keep, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
    print(dict(log))
    print(len(keep), Counter(x["subtype"] for x in keep))


if __name__ == "__main__":
    main(*sys.argv[1:4])
