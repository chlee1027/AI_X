"""analyze_etc.py 가 실제 페이지에서 찾은 후보 -> etc.yaml (생성 없음).

거르는 기준
  link_cloaking : 앵커 텍스트가 일반 안내 문구(CTA)인 것만. t.me 등 메신저·주요 정상 도메인 제외. (사이트, href) 중복 제거
  zero_width    : evidence 에 보이지 않는 문자가 실제로 있는 것. (사이트, 원문) 중복 제거
  meta_cloaking : 원문 head 의 해당 태그를 그대로 html 로. (사이트, 위치, 값) 중복 제거
  encoding      : 디코딩 결과가 설정 JSON·코드처럼 보이면 제외. 원문 조각 그대로
  css_content   : 그대로
그리고 doorway 실측 4건(etc_real.yaml)을 앞에 붙인다.

사용: python build_etc_found.py out.yaml etc_real.yaml found1.json [found2.json ...]
"""
import json
import re
import sys
import unicodedata
from html import escape
from pathlib import Path
from urllib.parse import unquote, urlsplit

import yaml

CTA = re.compile(r"바로\s*가기|바로\s*가입|클릭|시작하기|접속|입장|로그인|회원\s*가입|가입하기|홈페이지|자세히|더\s*보기|여기|"
                 r"공식\s*(파트너|사이트)|이동|링크|사이트\s*바로|주소|안내|문의하기|신청|이벤트", re.I)
NOT_DEST = re.compile(r"(^|\.)(t\.me|telegram\.(me|org)|open\.kakao\.com|pf\.kakao\.com|line\.me|wa\.me|notion\.so|notion\.site)$", re.I)
# 앵커에서 안내 문구를 뺀 나머지로 허용하는 일반 낱말 (브랜드명 「인디고」 같은 것은 안 된다)
GENERIC_RESID = re.compile(r"^(지금|공식|파트너|불가시|불가|시|사이트|여기|링크|바로|홈|안내|문의|빠른|최신|새|전용|고객|go|GO|Go|\d)*$")  # 2026-10-10 「바로가기 go !!」「1. 사이트 바로가기」
INVIS = re.compile("[​-‏⁠-⁤﻿­͏ᅟᅠㅤﾠ᠎]")
# 전화번호: 0 을 o 로 바꾸고 ―﹣‒⸻ 같은 대시를 쓴 꼴까지 (o10―8359﹣o661)
# 구분자에 자모 ㅡ 도 넣는다 (Oloㅡ8359 O6611 꼴, 2026-10-04)
PHONE = re.compile(r"[0oOⓞ⓪０][\W_ㅡ]{0,3}[1lI①１][\W_ㅡ]{0,3}[016789oO０](?:[\W_ㅡ]{0,3}[\doOlI０-９]){7,8}")
AD_WORD = re.compile(r"카지노|바카라|토토|슬롯|먹튀|놀이터|홀덤|대출|디비|DB|해킹|해커|룸싸롱|룸살롱|오피|비아그라|시알리스|"
                     r"내구제|코인|주식|선물|로또|보험|먹콜|메이저", re.I)
# 사이트당 상한: 한 사이트가 데이터를 덮지 않게. 서로 다른 글에서 나온 것만 세므로 제로폭은 10까지 둔다
URL_ENC = re.compile(r"(?:%[0-9A-Fa-f]{2}){6,}(?:[^&#\s]*(?:%[0-9A-Fa-f]{2})+)*")
ENC_AD = re.compile(r"해선|해킹|디비|db|대출|코인|로또|주식|증권|카지노|토토|바카라|슬롯|홀덤|비아그라|출장|텔레", re.I)
META_JS_EMPTY = {"co-o-zam.co.kr"}
PER_HOST = {"link_cloaking": 10, "zero_width": 10, "meta_cloaking": 10, "css_content": 5, "encoding": 5}
EXTRA = {"zero_width": "ZERO_WIDTH", "link_cloaking": "LINK_CLOAKING", "css_content": "CSS_CONTENT",
         "meta_cloaking": "META_CLOAKING", "encoding": "ENCODING"}


ZW_NEAR = re.compile(r"카지노|바카라|토토|슬롯|먹튀|놀이터|홀덤|바둑이|꽁머니|에볼루션|사이트|비아그라|시알리스|씨알리스|레비트라|"
                     r"카마그라|정력|출장|안마|오피|콜걸|건마|조건만남|룸싸롱|유흥|내구제|대출|클릭|이동|구매|텔레|카톡|도메인|주소|가입|"
                     r"o10|010|com|COM|net|top", re.I)


def zw_meaningful(ev: str) -> bool:
    """보이지 않는 문자가 광고 키워드·연락처·도메인 바로 안이나 옆(±4자)에 있어야 회피 목적으로 본다.
    이모지를 잇는 U+200D(💁🏻‍♂️)와 긴 본문에 복사로 딸려 온 제로폭은 뺀다."""
    for m in INVIS.finditer(ev):
        i = m.start()
        prev = ev[i - 1] if i else ""
        nxt = ev[i + 1] if i + 1 < len(ev) else ""
        if m.group(0) == "‍" and (unicodedata.category(prev) in ("So", "Sk") or 0x1F3FB <= ord(prev or "a") <= 0x1F3FF
                                      or nxt in "♀♂⚕⚖✈❤"):
            continue
        window = INVIS.sub("", ev[max(0, i - 4): i + 5])
        if ZW_NEAR.search(window):
            return True
    return False


def mask(s: str) -> str:
    # 앞 세 자리(난독화 모양 포함)만 남기고 나머지 숫자·o 는 X
    return PHONE.sub(lambda m: m.group(0)[:3] + re.sub(r"[\doOlI]", "X", m.group(0)[3:]), s)


def head_tag(raw: str, loc: str, val: str) -> str | None:
    """원문 head 에서 해당 태그 원문을 그대로 꺼낸다."""
    """같은 이름의 태그가 여러 개면(사이트 기본값 + 글 메타) 값이 evidence 와 맞는 것을 고른다."""
    from html import unescape
    if loc == "head > title":
        pat = r"<title[^>]*>.*?</title>"
    elif loc.startswith("script"):
        pat = r"<script[^>]+application/ld\+json[^>]*>.*?</script>"
    else:
        attr, name = re.match(r'meta\[(\w+)="([^"]+)"\]', loc).groups()
        pat = rf"<meta[^>]*\b{attr}=[\"']{re.escape(name)}[\"'][^>]*>"
    head = val[:30]
    for m in re.finditer(pat, raw, re.S | (0 if loc.startswith("meta") else re.I)):
        if head in unescape(m.group(0)):
            return m.group(0)
    return None


def main(out: str, real: str, founds: list[str]) -> None:
    items = yaml.safe_load(Path(real).read_text(encoding="utf-8")) or []
    from collections import Counter as _C
    seen, rows, per_host = set(), [], _C()
    for fj in founds:
        rows += json.loads(Path(fj).read_text(encoding="utf-8"))
    # 사이트당 상한이 소프트 하이픈(U+00AD)만 쓴 제로폭으로 먼저 차지 않게 그 행을 뒤로 (2026-10-11)
    rows.sort(key=lambda x: x["kind"] == "zero_width" and x.get("chars") == ["U+00AD"])
    for x in rows:
        kind, host = x["kind"], urlsplit(x["url"]).netloc
        note = ""
        if kind == "link_cloaking" and URL_ENC.search(x["ev"]):
            # 링크 주소 쿼리에 광고 문구를 퍼센트 인코딩해 넣은 경우: 화면 앵커와 달리 광고는 인코딩된 채 href 에만 있다
            enc_part = max(URL_ENC.findall(x["ev"]), key=len)
            dec = unquote(enc_part)
            if (AD_WORD.search(dec) or ENC_AD.search(dec)) and re.search(r"@\w{4,}|카지노|토토|대출|디비|DB|비아그라|출장", dec, re.I):
                ekey = ("encoding", host, re.sub(r"\W", "", dec)[:40])
                if ekey not in seen and per_host[("encoding", host)] < PER_HOST["encoding"] and x.get("loc"):
                    seen.add(ekey)
                    per_host[("encoding", host)] += 1
                    items.append({"id": "", "category": "ETC", "subtype": "encoding", "html": x["snippet"], "css": "",
                                  "evidence_text": enc_part, "expected_location": x["loc"], "is_positive": True,
                                  "extra_finding": "ENCODING",
                                  "source": f"실측: {x['url']} (2026-10-03 수집, JS 끄고 원문 렌더링)",
                                  "notes": f"URL 퍼센트 인코딩(엔티티·Base64 아님). 광고 문구가 링크 주소 쿼리에만 인코딩되어 있고 "
                                           f"화면 앵커는 '{x['anchor'][:30]}'. 디코딩: {dec[:80]}. 목적지는 무관한 외부 사이트의 검색 페이지(검색창 악용), 미방문"})
        if kind == "link_cloaking":
            dest = urlsplit(x["ev"]).hostname or ""
            # 앵커에서 안내 문구를 뺀 나머지에 광고 어휘가 남으면 앵커 자체가 광고이므로 클로킹이 아니다
            residual = re.sub(r"[\s\W_]+", "", CTA.sub("", x["anchor"]))
            # 정상 사이트 검색 페이지에 스팸 핸들을 검색어로 넣은 링크(검색창 악용)는 목적지가 도박 도메인이 아니므로 뺀다
            search_abuse = re.search(r"/search|catalogsearch|[?&](q|text|s|kwd|query|keyword)=", x["ev"], re.I)
            if (not CTA.search(x["anchor"]) or NOT_DEST.search(dest) or AD_WORD.search(residual)
                    or not GENERIC_RESID.match(residual) or search_abuse):
                continue
            key = (kind, host, x["ev"], re.sub(r"\s+", "", x["anchor"]))  # 같은 목적지라도 앵커 문구가 다르면 다른 요소
            html, ev, loc = x["snippet"], x["ev"], x["loc"]
            note = f"앵커 텍스트 '{x['anchor']}' 는 일반 안내 문구, href 는 글이 광고하는 외부 도메인. 목적지 미방문"
        elif kind == "zero_width":
            if not INVIS.search(x["ev"]) or not zw_meaningful(x["ev"]):
                continue
            # 같은 글 제목이 「> 게시판명」만 붙어 두 번 나오는 경우를 합치려고 앞 60자로 비교
            key = (kind, host, re.sub(r"\s*>\s*[^>]{1,20}$", "", re.sub(r"\s+", " ", x["ev"]))[:60])
            html, ev, loc = mask(x["snippet"]), mask(x["ev"]), x["loc"]
            note = f"보이지 않는 문자 {', '.join(x['chars'])} 가 광고 문구 안에 들어 있음"
        elif kind == "meta_cloaking":
            # JS 를 끄면 본문 전체가 비어 보이는 사이트는 「본문엔 광고 없음」이 렌더링 방식 탓이므로 뺀다 (2026-10-04 확인)
            if host in META_JS_EMPTY:
                continue
            raw = Path(x["file"]).read_bytes().decode("utf-8", "replace")
            tag = head_tag(raw, x["loc"], x["ev"])
            if not tag:
                continue
            key = (kind, host, x["loc"], x["ev"][:60])
            html, ev, loc = tag, x["ev"], x["loc"]
            note = "화면 본문에는 광고 어휘가 없고 head 에만 남아 있음 (원 글 삭제 후 404 화면에도 메타가 남은 경우 포함)"
        elif kind == "encoding":
            dec = x.get("decoded", "")
            if dec.lstrip().startswith(("{", "[")) or re.search(r"function|var |IS_\w+", dec):
                continue
            key = (kind, host, x["ev"][:60])
            html, ev, loc = None, x["ev"], None   # 원문 조각은 수동 확인 후 넣는다 (아래에서 건너뜀)
            continue
        else:  # css_content
            key = (kind, host, x["ev"][:60])
            html, ev, loc = x["snippet"], x["ev"], x["loc"]
            note = f"{x.get('pseudo')} content 로 광고 문구 주입"
        if key in seen or not loc or not html or not str(ev).strip():
            continue
        if per_host[(kind, host)] >= PER_HOST[kind]:
            continue
        per_host[(kind, host)] += 1
        seen.add(key)
        items.append({"id": "", "category": "ETC", "subtype": kind, "html": html, "css": "", "evidence_text": ev,
                      "expected_location": loc, "is_positive": True, "extra_finding": EXTRA[kind],
                      "source": f"실측: {x['url']} (2026-10-03 수집, JS 끄고 원문 렌더링)", "notes": note})
    for i, it in enumerate(items, 1):
        it["id"] = f"ET-{i:03d}"
    Path(out).write_text(yaml.safe_dump(items, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
    from collections import Counter
    print(len(items), Counter(i["subtype"] for i in items))
    print(Counter((i["subtype"], urlsplit(i["source"].split(" ")[1]).netloc) for i in items))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
