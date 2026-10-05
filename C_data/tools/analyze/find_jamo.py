"""실측 원문 색인(corpus.jsonl)에서 자모 분해 광고를 찾아 jamo.yaml 양식 후보로 만든다.

찾는 것
  compat_full      : 낱말 하나가 통째로 호환자모(ㄱ-ㅣ, U+3131~318E)로 풀린 것. 다시 묶으면 광고 어휘 (ㅂㅏㅋㅏㄹㅏ -> 바카라)
  conjoining_u1100 : 조합자모(U+1100~11FF)로 적힌 낱말. 다시 묶으면(NFC) 광고 어휘
조건
  - 다시 묶은 낱말이 광고 어휘(AD)를 담아야 한다
  - evidence(그 낱말이 든 문장, 앞뒤 최대 90자) 전체를 다시 묶었을 때도 광고 내용이어야 한다
  - 같은 사이트·같은 분해형은 한 번만, 같은 evidence 는 한 번만
  - 전화번호는 앞 세 자리 모양만 남기고 가린다
사용: python find_jamo.py corpus.jsonl out.yaml [exclude_hosts_csv]
"""
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "build"))  # fix_jamo.mask (전화번호 가림)
from fix_jamo import mask  # noqa: E402

CHO = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
JUNG = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
JONG = ["", "ㄱ", "ㄲ", "ㄳ", "ㄴ", "ㄵ", "ㄶ", "ㄷ", "ㄹ", "ㄺ", "ㄻ", "ㄼ", "ㄽ", "ㄾ", "ㄿ", "ㅀ", "ㅁ", "ㅂ", "ㅄ", "ㅅ",
        "ㅆ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"]
AD = re.compile(r"카지노|바카라|토토|슬롯|홀덤|바둑이|먹튀|놀이터|꽁머니|첫충|가입|베팅|배팅|에볼루션|파워볼|"
                r"비아그라|시알리스|레비트라|출장|안마|오피|조건만남|콜걸|대출|내구제|작업|텔레|카톡|도박")
# 호환자모로만 된 낱말: 초성+중성(+종성) 이 두 번 이상
FULL = re.compile(rf"(?:[{CHO}][{JUNG}](?:[{''.join(j for j in JONG if j)}](?![{JUNG}]))?){{2,}}")
CONJ = re.compile(r"[ᄀ-ᇿ가-힣]*[ᄀ-ᅟ][ᅠ-ᆧ][ᆨ-ᇿ]?[ᄀ-ᇿ가-힣]*")


def compose(seq: str) -> str:
    out, i = [], 0
    while i < len(seq):
        if i + 1 < len(seq) and seq[i] in CHO and seq[i + 1] in JUNG:
            c, v = CHO.index(seq[i]), JUNG.index(seq[i + 1])
            t = 0
            if i + 2 < len(seq) and seq[i + 2] in JONG and not (i + 3 < len(seq) and seq[i + 3] in JUNG):
                t = JONG.index(seq[i + 2])
                i += 1
            out.append(chr(0xAC00 + (c * 21 + v) * 28 + t))
            i += 2
        else:
            out.append(seq[i])
            i += 1
    return "".join(out)


def context(t: str, s: int, e: int) -> str:
    a = max(t.rfind("\n", 0, s), s - 90)
    b = t.find("\n", e)
    b = min(b if b != -1 else len(t), e + 90)
    return re.sub(r"\s+", " ", t[a + 1 if t[a:a + 1] == "\n" else a:b]).strip()


def main(corpus: str, out: str, exclude: str = "") -> None:
    ex = set(h for h in exclude.split(",") if h)
    items, seen_form, seen_ev = [], set(), set()
    with open(corpus, encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r["host"].removeprefix("www.") in ex:
                continue
            t = r["text"]
            for kind, rx in (("compat_full", FULL), ("conjoining_u1100", CONJ)):
                for m in rx.finditer(t):
                    raw = m.group(0)
                    word = compose(raw) if kind == "compat_full" else unicodedata.normalize("NFC", raw)
                    if not AD.search(word):
                        continue
                    ev = context(t, m.start(), m.end())
                    whole = compose(unicodedata.normalize("NFC", ev))
                    if not AD.search(whole) or len(ev) < 6:
                        continue
                    key_f = (r["host"], kind, raw)
                    key_e = re.sub(r"\s+", "", ev)
                    if key_f in seen_form or key_e in seen_ev:
                        continue
                    seen_form.add(key_f)
                    seen_ev.add(key_e)
                    items.append({"kind": kind, "url": r["url"], "host": r["host"], "date": r["fetched_at"][:10],
                                  "raw": raw, "word": word, "evidence": mask(ev)})
    Path(out).write_text(yaml.safe_dump(items, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
    print(len(items), Counter((i["kind"], i["host"]) for i in items).most_common(40))


if __name__ == "__main__":
    main(*sys.argv[1:4])
