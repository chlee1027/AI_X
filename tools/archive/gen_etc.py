"""ETC 생성분 (실측으로 못 채운 나머지).

틀(carrier) = 2026-10-03 실제로 받은 공공·기관 게시판 DOM 구조 (클래스·태그 체인 그대로)
광고 문구  = 같은 날 검색·수집한 실제 스팸 문구의 구조. 브랜드·도메인·텔레그램 핸들은 같은 형태의 가명으로 바꿨다
            (실제 업자 연락처를 테스트 데이터에 퍼뜨리지 않기 위해).
수법 변형  = 하위 유형마다 축(문자 종류·삽입 위치·틀·href 형태 등)을 돌려 같은 모양이 반복되지 않게 한다.

사용: python gen_etc.py start_index out.yaml   (start_index 는 실사례 뒤 번호)
"""
import base64
import html as H
import json
import random
import sys
from pathlib import Path
from urllib.parse import quote

import yaml

random.seed(20261003)

# ---- 실제 게시판 틀: (출처, 여는 태그들, 닫는 태그들). 대상 요소는 가장 안쪽에 들어간다
CARRIERS = [
    ("진도군청 자유게시판 댓글 (jindo.go.kr B0047)",
     '<div class="comment_list"><ul><li><dl class="reply_bg" style="margin-left:0px"><dt>방문자<span class="date">2026-09-14 10:21</span></dt><dd id="comment_{n}">',
     "</dd></dl></li></ul></div>", "div.comment_list dd#comment_{n}"),
    ("김해시 포토매니저 사진요청 본문 (gimhae.go.kr SmartPhoto)",
     '<div class="bbs1view1"><h1 class="h1">사진 요청드립니다</h1><div class="substance">',
     "</div></div>", "div.bbs1view1 > div.substance"),
    ("CBMC 그누보드 본문 (cbmc.or.kr bo_v_con)",
     '<section id="bo_v_atc"><h2 id="bo_v_atc_title">본문</h2><div id="bo_v_con"><div class="container clearfix"><p>',
     "</p></div></div></section>", "div#bo_v_con p"),
    # 아래 셋은 바깥 체인만 실측(글이 삭제돼 본문 칸은 비어 있었다). 안쪽 한 단은 빈 칸 자리의 실제 태그
    ("익산 서동축제 게시판 보기 (seodong.iksan.go.kr inner.php, section.subcontent > div.contsBox 실측)",
     '<section class="subcontent"><div class="contsBox"><div class="third_tab"></div><div class="">',
     "</div></div></section>", "section.subcontent > div.contsBox > div:nth-of-type(2)"),
    ("영진전문대 건축과 게시판 (arch.yju.ac.kr, div#contents > div.sub_contents 실측)",
     '<div id="contents"><div class="sub_contents">',
     "</div></div>", "div#contents > div.sub_contents"),
    ("김포대 대학자체평가 (ukp.ac.kr, div#content > article.single-page-content 실측)",
     '<div id="content" class="col-md-9 revert-layout" role="main"><article class="single-page-content">',
     "</article></div>", "div#content > article.single-page-content"),
]

# ---- 실제 스팸 문구 구조 (가명 처리). 원문 출처는 notes 에 적는다
PHRASES = [
    ("꽁머니 구글검색 빠른주소 2025 토토 카지노 승리의 첫걸음", "김해시 포토매니저 스팸 제목 구조"),
    ("안전놀이터 【룰루보증.com / 가입코드 7000】 토토사이트추천", "KAIST·전북대 게시판 스팸 제목 구조"),
    ("배팅의민족 『 로마나벳.com 』 가입코드 vip", "영진전문대 취업Q&A 스팸 제목 구조"),
    ("토토 회원유입 프로그램 텔레 @MOAS0FTKR", "영주 cji 방명록 스팸 제목 구조"),
    ("스타마켓 OKADO97.COM 토토주소 놀이터 도메인", "ssdj.or.kr 커뮤니티 스팸 제목 구조"),
    ("안전놀이터 〈홍보 텔 @oxo9090〉 우회링크", "김포대 대학자체평가 스팸 제목 구조"),
    ("썬배트 공식 도메인 먹튀검증 메이저업체 바카라사이트", "익산 서동축제 게시판 스팸 제목 구조"),
    ("스포츠중계 구글검색 벳모어 실시간 무료중계", "익산 서동축제 게시판 스팸 제목 구조"),
    ("에볼루션 사이트 kr09.com 코드 88889 바카라 하는 법", "검색 결과 스팸 제목 구조"),
    ("카지노 보증 업체 제이세븐 먹튀 없는 사이트", "진도군청 자유게시판 댓글 스팸 구조"),
    ("먹튀검증 안전놀이터 상담 텔레그램 @promo_7070", "요강 예시 어휘 구조"),
    ("첫충 30% 매충 10% 꽁머니 지급 슬롯사이트", "요강 예시·유인어 구조"),
]
KEYWORDS = ["카지노", "바카라", "토토", "놀이터", "꽁머니", "먹튀", "슬롯", "첫충", "벳"]

ZWS = ["​", "‌", "‍", "⁠", "﻿"]
ZW_NAME = {"​": "U+200B", "‌": "U+200C", "‍": "U+200D", "⁠": "U+2060", "﻿": "U+FEFF"}

NORMAL_ANCHOR = ["자세히 보기", "원문 보기", "관련 사이트", "첨부파일 다운로드", "홈페이지 바로가기", "참고 자료",
                 "행사 안내 바로가기", "신청서 양식", "출처", "더보기", "이벤트 안내", "공지사항 전문"]
FAKE_HOSTS = ["qwkz88.com", "wnnhx.com", "blk7329.com", "gate-kr0611.net", "vv77bt.top", "rrk3.xyz", "hm-krclub.com",
              "kr8890.com", "jjbt22.net", "zk-play.top"]


def wrap(ci: int, inner_open: str, inner_close: str, n: int) -> tuple[str, str]:
    src, op, cl, loc = CARRIERS[ci]
    return op.format(n=n) + inner_open, inner_close + cl, src, loc.format(n=n)


def zero_width(i: int, n: int) -> dict:
    phrase, origin = PHRASES[i % len(PHRASES)]
    zw = ZWS[i % len(ZWS)] if i % 6 else None  # 6번째마다 여러 종류 섞기
    mode = ["each_char", "one_mid", "domain_or_handle", "all_keywords", "between_words"][i % 5]
    text = phrase
    kws = [k for k in KEYWORDS if k in text] or [text.split()[0]]
    pick = lambda: zw or random.choice(ZWS)  # noqa: E731
    if mode == "each_char":
        k = kws[0]
        text = text.replace(k, pick().join(k), 1)
    elif mode == "one_mid":
        k = max(kws, key=len)
        m = len(k) // 2 or 1
        text = text.replace(k, k[:m] + pick() + k[m:], 1)
    elif mode == "domain_or_handle":
        import re
        m = re.search(r"[@A-Za-z0-9가-힣]+\.(?:com|COM)|@[A-Za-z0-9_]+", text)
        tok = m.group(0) if m else max(kws, key=len)
        text = text.replace(tok, pick().join(tok) if len(tok) > 1 else tok + pick(), 1)
    elif mode == "all_keywords":
        for k in kws:
            text = text.replace(k, k[0] + pick() + k[1:])
    else:
        text = text.replace(" ", " " + pick(), 3)
    ci = i % len(CARRIERS)
    tag = ["span", "strong", "a", "em", "span"][i % 5]
    attrs = ' href="#"' if tag == "a" else ""
    cls = f' class="t{i}"'
    o, c, src, loc = wrap(ci, f"<{tag}{cls}{attrs}>", f"</{tag}>", 40000 + i)
    used = sorted({ZW_NAME[ch] for ch in text if ch in ZW_NAME})
    return dict(subtype="zero_width", html=o + H.escape(text, quote=False) + c, css="",
                evidence_text=text, expected_location=f"{loc} > {tag}.t{i}",
                source=f"자체 생성 (틀: {src} / 문구: {origin})",
                notes=f"제로폭 {','.join(used)} · 삽입 방식 {mode}")


def link_cloaking(i: int, n: int) -> dict:
    text = NORMAL_ANCHOR[i % len(NORMAL_ANCHOR)]
    host = FAKE_HOSTS[i % len(FAKE_HOSTS)]
    form = ["direct", "gate_path", "shortener", "pages_dev", "blogspot", "open_redirect", "open_redirect2", "query_ref"][i % 8]
    href = {
        "direct": f"https://{host}/",
        "gate_path": f"https://{host}/gate/kr/kr0{random.randint(10000, 99999)}.html",
        "shortener": f"https://bit.ly/{random.choice(['hm', 'kr', 'vip'])}_{random.choice(['krclub', 'event', 'go'])}{i}",
        "pages_dev": f"https://{host.split('.')[0]}-hub.pages.dev/",
        "blogspot": f"https://{host.split('.')[0]}{i}.blogspot.com/",
        "open_redirect": f"http://ad1.dyntracker.com/set.aspx?dt_url=https://{host}/",
        "open_redirect2": f"http://esafety.cn/blog/go.asp?url=https://{host}/",
        "query_ref": f"https://{host}/?ref=kr{i}&code=vip",
    }[form]
    ci = (i + 2) % len(CARRIERS)
    place = ["inline", "attach", "related"][i % 3]
    if place == "attach":
        inner_o, inner_c = '<div class="attach1"><ul><li>', "</li></ul></div>"
        loc_tail = "div.attach1 > ul > li > a"
    elif place == "related":
        inner_o, inner_c = '<ul class="link_list"><li class="item">', "</li></ul>"
        loc_tail = "ul.link_list > li.item > a"
    else:
        inner_o, inner_c = "<span>행사 관련 내용은 </span>", "<span> 을(를) 참고하세요.</span>"
        loc_tail = "a"
    o, c, src, loc = wrap(ci, inner_o, inner_c, 41000 + i)
    a = f'<a href="{H.escape(href)}" target="_blank" rel="nofollow">{text}</a>'
    return dict(subtype="link_cloaking", html=o + a + c, css="", evidence_text=href,
                expected_location=f"{loc} {loc_tail}",
                source=f"자체 생성 (틀: {src} / href 형태: 실측 {form})",
                notes=f"앵커 텍스트 '{text}' 는 정상 문구, href 는 가명 도박 도메인. 배치 {place}")


def css_content(i: int, n: int) -> dict:
    phrase, origin = PHRASES[(i * 5) % len(PHRASES)]
    mode = ["before_literal", "after_literal", "attr_data", "css_escape", "split_before_after"][i % 5]
    cls = f"ad{i}"
    if mode == "before_literal":
        css, inner, ev = f'.{cls}::before {{ content: "{phrase}"; }}', f'<span class="{cls}"></span>', phrase
    elif mode == "after_literal":
        css, inner, ev = (f'.{cls}::after {{ content: "{phrase}"; font-size: 12px; color: #666; }}',
                          f'<span class="{cls}">문의는 아래로</span>', phrase)
    elif mode == "attr_data":
        css = f".{cls}::before {{ content: attr(data-note); }}"
        inner, ev = f'<span class="{cls}" data-note="{H.escape(phrase)}"></span>', phrase
    elif mode == "css_escape":
        esc = "".join(f"\\{ord(ch):X} " if ord(ch) > 127 else ch for ch in phrase)
        css, inner, ev = f'.{cls}::before {{ content: "{esc}"; }}', f'<i class="{cls}"></i>', esc
    else:
        a, b = phrase[: len(phrase) // 2], phrase[len(phrase) // 2:]
        css = f'.{cls}::before {{ content: "{a}"; }} .{cls}::after {{ content: "{b}"; }}'
        inner, ev = f'<span class="{cls}"></span>', a
    ci = (i + 4) % len(CARRIERS)
    o, c, src, loc = wrap(ci, "", "", 42000 + i)
    return dict(subtype="css_content", html=o + inner + c, css=css, evidence_text=ev,
                expected_location=f"{loc} > .{cls}",
                source=f"자체 생성 (틀: {src} / 문구: {origin})",
                notes=f"CSS 의사 요소 주입 {mode}. DOM 텍스트에는 광고가 없다")


HEAD_BASE = ('<meta name="viewport" content="width=device-width,initial-scale=1.0" />'
             '<meta name="robots" content="index, follow" /><meta name="author" content="서동축제" />'
             '<meta name="keywords" content="서동축제, 익산문화관광재단, 익산, 문화, 백제캠핑" />')


def meta_cloaking(i: int, n: int) -> dict:
    phrase, origin = PHRASES[(i * 7 + 1) % len(PHRASES)]
    slot = ["title", "description", "og_title", "og_description", "jsonld"][i % 5]
    title = "백제캠핑 | 서동축제"
    desc = "서동축제 백제캠핑 - 익산문화관광재단"
    ogt, ogd, ld = "익산 서동축제", "백제의 숨결, 천년의 사랑 익산서동축제에서 여러분을 초대합니다.", None
    if slot == "title":
        title = phrase + " | 서동축제"
        loc, ev = "head > title", phrase
    elif slot == "description":
        desc, loc, ev = phrase, 'meta[name="description"]', phrase
    elif slot == "og_title":
        ogt, loc, ev = phrase, 'meta[property="og:title"]', phrase
    elif slot == "og_description":
        ogd, loc, ev = phrase, 'meta[property="og:description"]', phrase
    else:
        ld = json.dumps({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": phrase, "item": "https://seodong.iksan.go.kr/"}]},
            ensure_ascii=False)
        loc, ev = 'script[type="application/ld+json"]', phrase
    head = (f"<title>{H.escape(title)}</title>" + HEAD_BASE +
            f'<meta name="description" content="{H.escape(desc)}" />'
            f'<meta property="og:title" content="{H.escape(ogt)}" />'
            f'<meta property="og:description" content="{H.escape(ogd)}" />'
            + (f'<script type="application/ld+json">{ld}</script>' if ld else ""))
    return dict(subtype="meta_cloaking", html=head, css="", evidence_text=ev, expected_location=loc,
                source=f"자체 생성 (틀: 익산 서동축제 실제 head 메타 구성 / 문구: {origin} / 수법: 해킹 도어웨이의 title·JSON-LD 패턴)",
                notes=f"본문은 정상, {slot} 에만 광고")


def encoding(i: int, n: int) -> dict:
    phrase, origin = PHRASES[(i * 3 + 2) % len(PHRASES)]
    mode = ["dec_entity_all", "hex_entity_all", "entity_keyword_only", "base64_docwrite", "url_encoded_href"][i % 5]
    ci = (i + 1) % len(CARRIERS)
    if mode == "dec_entity_all":
        enc = "".join(f"&#{ord(ch)};" if ord(ch) > 127 else ch for ch in phrase)
        inner, loc_tail, ev = f'<span class="e{i}">{enc}</span>', f"span.e{i}", enc
    elif mode == "hex_entity_all":
        enc = "".join(f"&#x{ord(ch):X};" if ord(ch) > 127 else ch for ch in phrase)
        inner, loc_tail, ev = f'<span class="e{i}">{enc}</span>', f"span.e{i}", enc
    elif mode == "entity_keyword_only":
        k = next((k for k in KEYWORDS if k in phrase), phrase[:2])
        enc = phrase.replace(k, "".join(f"&#{ord(ch)};" for ch in k), 1)
        inner, loc_tail, ev = f'<span class="e{i}">{enc}</span>', f"span.e{i}", enc
    elif mode == "base64_docwrite":
        b = base64.b64encode(phrase.encode("utf-8")).decode()
        inner = (f'<div class="e{i}"><script>document.write(decodeURIComponent(escape(atob("{b}"))))</script></div>')
        loc_tail, ev = f"div.e{i}", b
    else:
        host = FAKE_HOSTS[i % len(FAKE_HOSTS)]
        q = quote(phrase)
        href = f"https://{host}/?q={q}"
        inner = f'<a class="e{i}" href="{href}">{quote(phrase.split()[0])}</a>'
        loc_tail, ev = f"a.e{i}", quote(phrase.split()[0])
    o, c, src, loc = wrap(ci, "", "", 43000 + i)
    return dict(subtype="encoding", html=o + inner + c, css="", evidence_text=ev,
                expected_location=f"{loc} > {loc_tail}",
                source=f"자체 생성 (틀: {src} / 문구: {origin})",
                notes=f"인코딩 {mode}. evidence_text 는 html 원문에 적힌 인코딩 그대로")


def main(start: str, out: str, counts: str = "30,26,20,10,10") -> None:
    n_zw, n_lc, n_css, n_meta, n_enc = map(int, counts.split(","))
    gens = [(zero_width, n_zw), (link_cloaking, n_lc), (css_content, n_css), (meta_cloaking, n_meta), (encoding, n_enc)]
    items, k = [], int(start)
    for fn, cnt in gens:
        for i in range(cnt):
            s = fn(i, k)
            items.append({"id": f"ET-{k:03d}", "category": "ETC", "subtype": s["subtype"], "html": s["html"],
                          "css": s["css"], "evidence_text": s["evidence_text"],
                          "expected_location": s["expected_location"], "is_positive": True,
                          "extra_finding": {"zero_width": "ZERO_WIDTH", "link_cloaking": "LINK_CLOAKING",
                                            "css_content": "CSS_CONTENT", "meta_cloaking": "META_CLOAKING",
                                            "encoding": "ENCODING"}[s["subtype"]],
                          "source": s["source"], "notes": s["notes"]})
            k += 1
    Path(out).write_text(yaml.safe_dump(items, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
    print(len(items), "개 생성")


if __name__ == "__main__":
    main(*sys.argv[1:4])
