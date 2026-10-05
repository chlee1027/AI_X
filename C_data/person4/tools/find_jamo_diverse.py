"""쏠림을 덜기 위한 JAMO 추가 후보 찾기 (2026-10-05).

실측 원문 색인에서 「완성형 낱말 속에 호환자모가 섞인」 광고 문장을 찾는다.
  partial_mix     : 낱말 안에 호환자모가 섞임 (텔ㄹㅔ그램, 사ㅇㅣ트, ㅂㅏ둑이)
  mixed_technique : 위에 더해 다른 회피 수법이 같은 문장에 겹침 (자모+영문 치환 ㅋr톡, 자모+기호 구분자, 자모+숫자 치환 등)
제외: 이미 jamo.yaml 에 있는 사이트(쏠림을 덜려는 목적), 같은 사이트는 2건까지, `탤ㄹH`·`ㅋㅌ` 꼴(이미 많음),
      evidence 를 다시 묶었을 때 광고 어휘가 없는 것. 전화번호는 가린다.
사용: python find_jamo_diverse.py corpus.jsonl jamo.yaml analyze_dir out.yaml
"""
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from fix_jamo import mask  # noqa: E402
from find_jamo import AD, compose, context  # noqa: E402

# 낱말 안에 끼어 있는 호환자모 (앞이나 뒤가 완성형 음절)
INWORD = re.compile(r"[가-힣]*(?:[가-힣][ㄱ-ㅣ]+|[ㄱ-ㅣ]+[가-힣])[가-힣ㄱ-ㅣ]*")
SKIP_FORM = re.compile(r"탤ㄹ[Hh]|^ㅋㅌ$")
OTHER = {"fullwidth", "symbol_sep", "digit_sub", "jamo_homoglyph", "spacing", "zero_width", "kana_sep", "case_mix",
         "punct_variant", "enclosed_alnum", "enclosed_hangul", "math_alnum", "dot_sub", "domain_spacing", "spelling_variant", "homoglyph"}


def main(corpus: str, jamo: str, analyze_dir: str, out: str) -> None:
    sys.path.insert(0, analyze_dir)
    import analyze_obf as A  # noqa: E402
    have_hosts = {re.sub(r"^www\.", "", (re.search(r"https?://([^/ ]+)", x["source"]) or [None, ""])[1])
                  for x in yaml.safe_load(Path(jamo).read_text(encoding="utf-8"))}
    per_host, seen, items = Counter(), set(), []
    for line in open(corpus, encoding="utf-8"):
        r = json.loads(line)
        h = re.sub(r"^www\.", "", r["host"])
        if h in have_hosts or h.endswith(".go.kr") or per_host[h] >= 2:
            continue
        t = unicodedata.normalize("NFC", r["text"])
        for m in INWORD.finditer(t):
            w = m.group(0)
            jam = "".join(re.findall(r"[ㄱ-ㅣ]+", w))
            if SKIP_FORM.search(w) or len(w) < 2 or w in ("ㅋㅋ", "ㅎㅎ"):
                continue
            ev = context(t, m.start(), m.end())
            if len(ev) < 8 or not AD.search(compose(ev)) or not AD.search(compose(w) + ev):
                continue
            k = re.sub(r"\s+", "", ev)
            if k in seen:
                continue
            feats = set(A.features(ev)) & OTHER
            kind = "mixed_technique" if feats else "partial_mix"
            seen.add(k)
            per_host[h] += 1
            items.append({"kind": kind, "host": h, "url": r["url"], "date": r["fetched_at"][:10], "word": w, "jamo": jam,
                          "other": sorted(feats), "evidence": mask(ev)})
            if per_host[h] >= 2:
                break
    Path(out).write_text(yaml.safe_dump(items, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
    print(len(items), Counter(i["kind"] for i in items))
    for i in items:
        print(i["kind"][:7], i["host"][:24], "|", i["word"], i["other"], "|", i["evidence"][:70])


if __name__ == "__main__":
    main(*sys.argv[1:5])
