"""실측 원문 색인에서 광고 어휘 후보를 뽑는다 (도박 핵심어·유인어·연락 수단).

각 후보마다 나온 페이지 수·사이트 수와 첫 출처 URL 을 남긴다. 공공기관(.go.kr) 페이지는 근거에서 뺀다
(광고 어휘의 근거는 실제 스팸 글이어야 하고, 기관 페이지에는 계도문이 섞이기 때문).

사용: python mine_terms.py corpus.jsonl out.json
"""
import json
import re
import sys
from collections import defaultdict

CORE = re.compile(r"(?:온라인|라이브|모바일|해외|사설|메이저|안전|정품|국내)?(?:카지노|바카라|토토|슬롯|홀덤|바둑이|파워볼|사다리|에볼루션|토지노|맞고|섯다|포커|룰렛|블랙잭|스포츠토토|먹튀)"
                  r"(?:사이트|주소|추천|검증|게임|솔루션|분양|임대|커뮤니티|순위|도메인|놀이터|업체|총판|매장|사이트추천|가입|제작|api|API|알)")
LURE = re.compile(r"(?:신규|매일|무한|가입|첫|돌발|주간|실시간|무제한|최대|즉시|전액|모든)?\s?"
                  r"(?:첫충|매충|돌발|페이백|콤프|입플|꽁머니|가입머니|가입쿠폰|롤링|루징|무제재|환전|충전|출석|보너스|먹튀\s?없는|먹튀\s?검증|보증금|쿠폰)"
                  r"(?:\s?\d{1,3}\s?%|\s?\d+만원?|\s?이벤트|\s?지급|\s?무제한|\s?보장|\s?가능)?")
CONTACT = re.compile(r"(?P<kw>[^\s\d:：;@,()\[\]【】{}<>\"'|]{1,8})\s?[:：;]?\s?@?(?P<id>[A-Za-z][A-Za-z0-9_]{3,15})(?![A-Za-z0-9_.])")
MSG = re.compile(r"텔|탤|톡|턱|카|ㅋ|ㅌ|라인|위챗|tele|kakao|line|wechat|문의|상담", re.I)


def main(corpus: str, out: str) -> None:
    found = {"core": defaultdict(lambda: [0, set(), ""]), "lure": defaultdict(lambda: [0, set(), ""]),
             "contact": defaultdict(lambda: [0, set(), "", ""])}
    for line in open(corpus, encoding="utf-8"):
        r = json.loads(line)
        if r["host"].endswith(".go.kr"):
            continue
        t = r["text"]
        for name, rx in (("core", CORE), ("lure", LURE)):
            for term in set(m.group(0).strip() for m in rx.finditer(t)):
                v = found[name][term]
                v[0] += 1
                v[1].add(r["host"])
                v[2] = v[2] or r["url"]
        for m in CONTACT.finditer(t):
            kw = m.group("kw")
            if not MSG.search(kw):
                continue
            v = found["contact"][kw]
            v[0] += 1
            v[1].add(r["host"])
            if not v[2]:
                v[2], v[3] = r["url"], t[max(0, m.start() - 20):m.end() + 10].replace("\n", " ")
    res = {k: sorted(([t, v[0], len(v[1]), *v[2:]] for t, v in d.items()), key=lambda z: (-z[2], -z[1])) for k, d in found.items()}
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    for k, rows in res.items():
        print("==", k, len(rows))
        print(" / ".join(f"{r[0]}({r[2]}곳)" for r in rows[:60]))


if __name__ == "__main__":
    main(*sys.argv[1:3])
