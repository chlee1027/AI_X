"""lexicon/seed.yaml 점검 결과 고치기 (2026-10-05).

바꾸는 것
1. contact
   - 공공기관 문서에서 온 상담 안내 문구(헬프라인 1336 등)는 광고 연락 수단이 아니라 정상 안내문이라 whitelist 로 옮김 (weight 0.0)
   - 일반어(문의·상담·라인 등)는 뺌
   - 남는 것과 새로 넣는 것은 「연락 수단 표기 + 아이디」 또는 「변형 전화번호」 정규식으로 만들고,
     실측 원문(corpus)에서 실제로 맞는 것만 남김. 출처는 처음 맞은 실측 페이지
2. gambling_core: 정상 문서에도 나오는 단독 낱말·합법 사행산업 낱말·규제 문서 용어는 gambling_weak 로 내림
   빈자리는 실측 스팸에서 2곳 이상 사이트에 나온 복합어로 채움
3. gambling_lure: 토토 커뮤니티(ttcs-1.com)를 출처로 한 어휘는 다른 실측 원문에서 확인되면 출처를 바꾸고, 안 되면 뺌
   일반어는 gambling_weak 로 내림. 빈자리는 실측 스팸 2곳 이상에 나온 유인 문구로 채움
4. adult: 정상 업종·일반어는 weight 0.3 으로 낮추고 notes 에 「단독 판정 금지」
5. 바뀌거나 새로 들어간 항목은 reviewed: false (사람 검수 전). 바뀐 이유는 change_note 에 적음

사용: python fix_lexicon.py seed.yaml corpus.jsonl mined.json out.yaml review.csv
"""
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

TODAY = "2026-10-05"
WEAK_CORE = {"도박", "확률형 아이템", "P2E", "가상화폐", "전자복권", "화투", "장기", "바둑", "골패", "주사위", "트럼프", "체스", "마작",
             "경품", "오락", "복권", "로또", "경마", "경륜", "경정", "체육진흥투표권", "체육진흥투표권 발매", "프로토", "소싸움",
             "사행산업", "홀덤펍", "스포츠 토토", "웹보드게임", "슬롯머신", "스크린 경마", "카지노", "토토", "베팅", "슬롯", "바카라",
             "파친코", "바다이야기", "사다리게임", "홀짝", "달팽이게임", "소셜그래프게임", "FX마진거래", "사설FX마진거래",
             "돈내기 게임", "사행성 게임", "사행성게임물", "온라인 즉석 및 실시간 게임", "파워볼 게임", "슬롯게임", "카지노게임"}
# 규제기관 문서에서 온 「유형 이름」. 광고는 스스로를 이렇게 부르지 않고 계도문·보도자료에 주로 나온다
POLICY_CORE = re.compile(r"불법|^사설 |^온라인 (도박|카지노|불법|스포츠)|^인터넷 도박|^스포츠도박|^사기도박|^온라인/라이브|^온라인 도박 사이트")
WEAK_LURE = {"신규", "루틴", "다양한 이벤트", "이벤트 제공", "신규 회원", "검증된", "회원 모집", "상시 업데이트", "국내 최초", "업계 최고",
             "대한민국 대표", "명품 사이트", "쿠폰", "이벤트 진행", "신규가입", "무료나눔", "연속출석", "자동적립", "국내 최고 배당", "고배당"}
WEAK_ADULT = {"마사지", "안마", "스웨디시", "커피배달", "유흥", "노래방", "고구려", "마사지샵", "왁싱샵", "아로마마사지", "솔로탈출",
              "이성만남", "만남앱", "만남어플", "싱글만남", "돌싱만남", "번개만남", "부킹만남", "업소추천", "유흥주점", "유흥업소", "휴게텔",
              "텐카페", "여성전용마사지", "여성전용안마", "토닥이", "감성스웨디시", "성인쉼터", "출장서비스", "노래빠"}
# 정상 공지(지역화폐·지원금 안내 등)에도 나오는 입출금 일반 문구. 유인어로 채우지 않는다
GENERIC_PAY = {"즉시지급", "100%지급", "매일지급", "당일지급", "최대지급", "실시간지급", "최대베팅", "최대배팅", "빠른입금", "즉시입금",
               "당일입금", "전액입금", "첫입금", "첫충전", "매일충전", "빠른충전", "전액지급", "즉시보너스", "최대출금", "빠른출금",
               # 쇼핑몰·멤버십 공지에도 흔한 쿠폰·보너스·입출금 낱말
               "환전", "충전", "쿠폰", "보너스", "출석", "보증금", "쿠폰지급", "쿠폰이벤트", "모든쿠폰", "즉시쿠폰", "모든보너스", "보너스지급",
               "가입쿠폰", "가입쿠폰이벤트", "가입쿠폰지급", "가입보너스", "신규보너스", "가입포인트", "가입이벤트", "보너스이벤트", "충전이벤트",
               "매일지급", "환전가능", "100%보너스", "보너스100%", "즉시출금", "즉시출금가능", "빠른환전"}
GENERIC_CONTACT = {"상담", "문의", "전화", "예약", "라인", "문의하기", "예약상담", "상담한적", "상담바랍니다", "디테일한상담", "방법문의",
                   "요율문의", "지원센터", "24콜센터", "상담진행가능합니다", "비밀상담", "상담원", "설치/문의", "안전상담", "24시간상담",
                   "신용상담", "예약문의환영", "문의안내", "24시친절상담", "상담해드립니다", "친절상담", "구입상담", "카톡내역복구",
                   "카톡내역조회", "카톡대화내용실시간보기", "카톡내역확인", "11채팅으로만", "1:1채팅으로만", "프진상담", "톡:"}
EXCLUDE_SRC = ("ttcs-1.com", "magino.co.kr")
HANDLE = r"\s{0,2}[:：;=]?\s{0,2}@?\s{0,2}[A-Za-z][A-Za-z0-9_]{3,15}"
# 연락 수단 표기 변형. 사이에 끼는 공백·점·쉼표·하이픈은 정규식에서 허용
MESSENGER = ["텔레그램", "텔레", "텔", "탤", "탤레", "탤래", "텔래", "텔래그램", "탤레그램", "텔레그렘", "텔그", "탤그", "텔ㄹㅔ그램", "텔ㄹㅔ", "텔ㄹ",
             "탤ㄹㅔ", "탤ㄹH", "탤ㄹh", "ㅌ레", "ㅌㄹ", "텔.레", "텔,레", "텔 레", "텔레ID", "텔레아이디", "텔레문의", "텔문의", "탤문의", "텔레그램문의",
             "텔레상담", "광고문의텔", "광고텔레", "Tele", "TELE", "Telegram", "telegram", "TG", "카톡", "카카오톡", "카톡ID", "카톡아이디", "카톡문의",
             "캬톡", "꺄톡", "까톡", "깨톡", "깨똑", "카턱", "카 턱", "카,턱", "카 ,턱", "턱.텔.레", "카턱.텔.레", "카·톡", "카-톡", "캬-톡", "카-툭", "카툭",
             "캬툑", "ㅋ톡", "ㅋr톡", "ㅋㅏ톡", "ㅋㅏ_톡", "ㄲㅏ톡", "ㅋㅌ", "카c톡", "카.톡", "카 톡", "캬 툑", "까 턱", "문의톡", "상담톡", "에약톡",
             "라인ID", "LINE", "라인아이디", "위챗", "wechat", "WeChat", "카톡/텔레", "텔레/카톡", "카톡 텔레", "ㅋㅏ톡/텔ㄹㅔ", "카톡 텔", "카 톡 텔 레"]
PHONES = {
    "010 공백·점 구분 번호": r"(?<!\d)010[\s.\-]{1,3}\d{3,4}[\s.\-]{1,3}\d{4}(?!\d)",
    "o1o·O1O 영문 o 치환 번호": r"(?<![A-Za-z0-9])[oO][1lI][oO][\s.\-ㅡ=+~]{0,3}[\dX]{3,4}[\s.\-ㅡ=+~]{0,3}[\dX]{4}",
    "0l0·OlO 영문 l 치환 번호": r"(?<![A-Za-z0-9])[0oO][lI][0oO][\s.\-ㅡ=+~]{0,3}[\dX]{3,4}[\s.\-ㅡ=+~]{0,3}[\dX]{4}",
    "전각 숫자 번호": r"[０0][１1][０0][\s.\-ㅡ=]{0,3}[０-９\dX]{3,4}[\s.\-ㅡ=]{0,3}[０-９\dX]{4}",
    "원 문자 숫자 번호": r"[ⓞ⓪0][①1][ⓞ⓪0][\s.\-ㅡ]{0,3}[①-⑨⓪\dX]{3,4}[\s.\-ㅡ]{0,3}[①-⑨⓪\dX]{4}",
    "자모 ㅡ 구분 번호": r"[0oO０][1lI１][0oO０]ㅡ[\d０-９X]{3,4}ㅡ[\d０-９X]{4}",
    "기호 구분 번호(➖·〓·◆·▶)": r"[0oO０][1lI１][0oO０][\s]?[➖〓◆▶↕⸺―﹣‒=]{1,2}[\s]?[\d０-９X]{3,4}[\s]?[➖〓◆▶↕⸺―﹣‒=]{1,2}[\s]?[\d０-９X]{4}",
    "숫자 낱자 띄어 쓴 번호": r"(?<!\d)[0oO] ?[1lI] ?[0oO] ?[\-.]? ?(?:\d ?){3,4}[\-.]? ?(?:\d ?){4}",
}

# 연락 수단을 링크·아이디 표기·번호 표기로 적는 꼴 (메신저 이름 없이도 연락처가 되는 것)
EXTRA_CONTACT = {
    "텔레그램 t.me 링크": r"t\.me/[A-Za-z0-9_]{3,}",
    "텔레그램 telegram.me 링크": r"telegram\.me/[A-Za-z0-9_]{3,}",
    "카카오 오픈채팅 링크": r"open\.kakao\.com/o/[A-Za-z0-9]{4,}",
    "카카오 채널 링크": r"pf\.kakao\.com/[A-Za-z0-9_]{3,}",
    "라인 친구 링크": r"line\.me/(?:R/)?ti/p/\S+",
    "왓츠앱 링크": r"wa\.me/\d{6,}",
    "ID·아이디 표기 + 아이디": r"(?:ID|Id|id|아이디)\s{0,2}[:：]\s{0,2}@?[A-Za-z][A-Za-z0-9_]{3,15}",
    "문의·상담·연락 + @아이디": r"(?:문의|상담|연락|채널)\s{0,2}[:：]?\s{0,2}@[A-Za-z][A-Za-z0-9_]{3,15}",
    "+82 국제번호": r"\+82[\s\-]?10[\s\-]?\d{3,4}[\s\-]?\d{4}",
    "010 하이픈 번호": r"(?<!\d)010-\d{3,4}-\d{4}(?!\d)",
    "010 붙여 쓴 번호": r"(?<!\d)010\d{8}(?!\d)",
    "공일공·영일영 한글 번호": r"(?:공일공|영일영)[\s\-.]?\d{3,4}",
    "쉼표 구분 번호": r"[0oO][1lI][0oO][,，]\s?\d{3,4}[,，]\s?\d{4}",
    "슬래시 구분 번호": r"[0oO][1lI][0oO]/\d{3,4}/\d{4}",
    "# 끼운 번호": r"[0oO]\W{0,2}[1lI!]\W{0,2}[0oO]\W{0,3}#\s?\d{4}\s?#\s?\d{4}",
    "괄호·대괄호 번호": r"[\[(（]\s?[0oO０][1lI１][0oO０]\s?[\])）]\s?[\d０-９X]{3,4}",
    "따옴표 끼운 번호": r"[0oO] ?[1lI] ?[0oO]\\?\" ?\d{3,4} ?\\?\" ?[\d ]{4,7}",
    "한글 숫자 섞은 번호(이0 등)": r"(?:이|공|영)[0oO]\.?\s?\d\s?\d{3},\s?\d{2}\s?\d{2}",
}

# 실측에서 본, 위 꼴에 안 걸리는 연락 표기
EXTRA_CONTACT2 = {
    "닮은꼴 쌍점(꞉ː∶﹕) + 아이디": r"[꞉ː∶﹕︰]\s{0,2}@?[A-Za-z][A-Za-z0-9_]{3,15}",
    "라인 + 영문숫자 아이디": r"라인\s{0,2}[:：#＃]?\s{0,2}[A-Za-z]{2,}\d{2,}",
    "초성 ㅌ + @아이디": r"ㅌ\s{0,2}@[A-Za-z][A-Za-z0-9_]{3,15}",
    "텔레&라인 병기": r"텔레\s?[&＆/]\s?라인",
    "상담텔 + 아이디": r"상담\s?텔\W{0,2}[A-Za-z]{2,}\d{2,}",
    "카카오톡 낱자 띄움": r"카\s카\s오\s톡",
}
# 원래 seed 의 contact 중 광고 전용 연락 문구(ygen.kr 실측). 일반어는 빼고 남김
KEEP_OLD_CONTACT = ["상담톡", "문의톡", "ㅋr톡", "예약상담-톡", "에약톡", "상담톡-", "문의톡:", "상담톡:", "오픈채팅", "텔레채널그룹",
                    "텔레채널/그룹", "구입상담문의", "돈믹싱문의", "유심칩매입문의", "선불유심매입문의", "비대면가전내구제문의",
                    "인터넷회선내구제문의", "신불자급전내구제문의", "법인소액작업대출문의", "후불폰유심매입문의", "핸드폰가전내구제방법문의"]

# 단체방·채널 참여를 부르는 연락 문구 (실측 스팸에서 확인)
EXTRA_CONTACT3 = {"오픈채팅방": r"오픈\s?채팅\s?방", "단톡방": r"단톡\s?방", "텔방·텔레방": r"텔레?\s?방", "텔레그램 채널": r"텔레그램\s?채널",
                  "홍보방": r"홍보\s?방", "소통방": r"소통\s?방", "24시 텔레": r"24시\s?텔레?"}


def loose_pattern(v: str) -> str:
    # 글자 사이에 공백·점·쉼표·하이픈·가운뎃점이 0~2개 끼어도 맞게
    chars = [re.escape(c) for c in v if not c.isspace()]
    return r"[\s.,\-·_]{0,2}".join(chars)


def find(corpus: list[dict], rx: re.Pattern, ad: re.Pattern) -> tuple[str, str] | None:
    for r in corpus:
        if r["host"].endswith(".go.kr") or any(s in r["host"] for s in EXCLUDE_SRC):
            continue
        for m in rx.finditer(r["text"]):
            ctx = r["text"][max(0, m.start() - 60):m.end() + 60]
            if ad.search(ctx):
                return r["url"], re.sub(r"\s+", " ", ctx)
    return None


AD = re.compile(r"카지노|바카라|토토|슬롯|홀덤|바둑이|먹튀|놀이터|첫충|매충|꽁머니|비아그라|시알리스|출장|안마|오피|조건만남|콜걸|대출|내구제|작업|"
                r"유심|급전|디비|DB|구글|찌라시|레플리카|명품|룸|가라오케|셔츠|텐프로|마사지|도박|솔루션|분양|파워볼|에볼루션|게임|텔레|텔ㄹ|도매")


def main(seed: str, corpus_path: str, mined_path: str, out: str, review: str) -> None:
    xs = yaml.safe_load(Path(seed).read_text(encoding="utf-8"))
    corpus = [json.loads(l) for l in open(corpus_path, encoding="utf-8")]
    mined = json.load(open(mined_path, encoding="utf-8"))
    have = {re.sub(r"\s+", "", x["term"].lower()) for x in xs}
    log = Counter()
    res = []

    def changed(x: dict, note: str) -> dict:
        x["reviewed"] = False
        x["change_note"] = (x.get("change_note", "") + f" {TODAY}: {note}").strip()
        return x

    for x in xs:
        cat, term, src = x["category"], x["term"], str(x["source"])
        if cat == "contact":
            if not src.startswith("http"):
                x["category"], x["weight"] = "whitelist", 0.0
                res.append(changed(x, "공공기관 상담 안내 문구라 광고 연락 수단이 아님 -> contact 에서 whitelist 로"))
                log["contact->whitelist"] += 1
            else:
                log["contact 재구성 대상"] += 1   # 아래에서 패턴으로 다시 만든다
            continue
        if cat == "gambling_core" and (term in WEAK_CORE or POLICY_CORE.search(term)):
            x["category"], x["weight"] = "gambling_weak", 0.1 if POLICY_CORE.search(term) else 0.2
            res.append(changed(x, "정상 문서(합법 사행산업·규제 문서·놀이 낱말)에도 나와 단독 판정하면 오탐 -> gambling_weak"))
            log["core->weak"] += 1
            continue
        if cat == "gambling_lure":
            if term in WEAK_LURE:
                if any(t in src for t in EXCLUDE_SRC):
                    hit = find(corpus, re.compile(re.escape(term)), AD)
                    if not hit:
                        log["lure(weak 대상) 출처 불법·대체 근거 없음 -> 제외"] += 1
                        continue
                    x["source"] = hit[0]
                x["category"], x["weight"] = "gambling_weak", 0.2
                res.append(changed(x, "일반 광고·안내 문구에도 쓰여 단독 판정하면 오탐 -> gambling_weak"))
                log["lure->weak"] += 1
                continue
            if any(s in src for s in EXCLUDE_SRC):
                hit = find(corpus, re.compile(re.escape(term)), AD)
                if hit:
                    x["source"] = hit[0]
                    res.append(changed(x, "출처가 토토 커뮤니티(ttcs-1.com, 불법 사이트)라 실측 공개 게시판 원문으로 출처 교체"))
                    log["lure 출처 교체"] += 1
                else:
                    log["lure 출처 불법·대체 근거 없음 -> 제외"] += 1
                continue
        if cat == "adult" and term in WEAK_ADULT:
            x["weight"] = 0.3
            x["notes"] = "정상 업종·일반어. 단독 출현으로 판정 금지, 다른 성인 어휘와 함께 나올 때만"
            res.append(changed(x, "정상 업종·일반어라 weight 1.0 -> 0.3"))
            log["adult weight 낮춤"] += 1
            continue
        res.append(x)

    # contact 다시 만들기: 연락 수단 변형 + 아이디, 변형 전화번호
    old_contact = {x["term"]: x for x in xs if x["category"] == "contact" and str(x["source"]).startswith("http")}
    contact = []
    for v in MESSENGER:
        pat = loose_pattern(v) + HANDLE
        hit = find(corpus, re.compile(pat), AD)
        src = hit[0] if hit else None
        if not src and v in old_contact and v not in GENERIC_CONTACT:
            src = old_contact[v]["source"]      # 원래 실측 출처(ygen.kr 등)를 유지
        if not src:
            log["연락 변형 실측 없음"] += 1
            continue
        contact.append({"term": f"{v} + 아이디", "category": "contact", "weight": 0.8, "pattern": pat, "source": src,
                        "reviewed": False, "change_note": f"{TODAY}: 연락 수단 표기 변형과 뒤따르는 아이디를 함께 잡는 정규식으로 새로 만듦. 실측 원문에서 일치 확인"})
    for name, pat in PHONES.items():
        hit = find(corpus, re.compile(pat), AD)
        if hit:
            contact.append({"term": name, "category": "contact", "weight": 0.8, "pattern": pat, "source": hit[0], "reviewed": False,
                            "change_note": f"{TODAY}: 광고에 쓰인 변형 전화번호 꼴. 실측 원문에서 일치 확인(번호 자체는 저장하지 않음)"})
        else:
            log["번호 꼴 실측 없음"] += 1
    for name, pat in EXTRA_CONTACT.items():
        hit = find(corpus, re.compile(pat), AD)
        if hit:
            contact.append({"term": name, "category": "contact", "weight": 0.8, "pattern": pat, "source": hit[0], "reviewed": False,
                            "change_note": f"{TODAY}: 광고에 쓰인 연락 수단 링크·표기 꼴. 실측 원문에서 일치 확인"})
        else:
            log["링크·표기 꼴 실측 없음"] += 1
    for name, pat in EXTRA_CONTACT2.items():
        hit = find(corpus, re.compile(pat), AD)
        if hit:
            contact.append({"term": name, "category": "contact", "weight": 0.8, "pattern": pat, "source": hit[0], "reviewed": False,
                            "change_note": f"{TODAY}: 실측 스팸의 연락 표기 꼴. 실측 원문에서 일치 확인"})
    # 정상 글에는 나올 일이 없는 변형 표기는 뒤에 아이디가 없어도 연락 신호로 넣는다 (탤ㄹH문의, ㄲㅏ톡 탤ㄹㅔ)
    for v in ["탤ㄹH", "탤ㄹh", "ㄲㅏ톡"]:
        pat = loose_pattern(v)
        hit = find(corpus, re.compile(pat), AD)
        if hit and f"{v} + 아이디" not in {c["term"] for c in contact}:
            contact.append({"term": f"{v} (표기 단독)", "category": "contact", "weight": 0.8, "pattern": pat, "source": hit[0],
                            "reviewed": False, "change_note": f"{TODAY}: 정상 글에 나오지 않는 메신저 이름 변형 표기. 실측 원문에서 일치 확인"})
    have_terms = {c["term"].split(" + ")[0] for c in contact}
    for t in KEEP_OLD_CONTACT:
        if t in old_contact and t.rstrip(":-") not in have_terms:
            o = dict(old_contact[t])
            o["pattern"] = loose_pattern(t.rstrip(":-"))
            o["weight"] = 0.8
            contact.append(changed(o, "광고 전용 연락 문구라 contact 에 남김. 낱말 사이 공백·기호를 허용하는 정규식으로 바꿈"))
            have_terms.add(t.rstrip(":-"))
    for name, pat in EXTRA_CONTACT3.items():
        hit = find(corpus, re.compile(pat), AD)
        if hit:
            contact.append({"term": name, "category": "contact", "weight": 0.8, "pattern": pat, "source": hit[0], "reviewed": False,
                            "change_note": f"{TODAY}: 단체방·채널 참여를 부르는 연락 문구. 실측 원문에서 일치 확인"})
    # 정규식이 같은 패턴은 하나만 (텔레/텔 레, 카톡/카 톡 은 loose 정규식이 같다)
    uniq, seen_p = [], set()
    for c_ in contact:
        if c_["pattern"] in seen_p:
            log["contact 같은 정규식 중복 제거"] += 1
            continue
        seen_p.add(c_["pattern"])
        uniq.append(c_)
    contact = uniq
    log["contact 새 패턴"] = len(contact)
    res += contact[:100]

    # core·lure 채우기: 실측 스팸 2곳 이상 사이트에 나온 복합어, 이미 있는 것과 겹치지 않게
    def fill(cat: str, rows: list, weight: float, note: str, min_host: int = 2, min_page: int = 1) -> None:
        need = 100 - sum(1 for x in res if x["category"] == cat)
        for term, n_page, n_host, url, *_ in rows:
            if need <= 0:
                break
            k = re.sub(r"\s+", "", term.lower())
            if n_host < min_host or n_page < min_page or k in have or len(term) < 2 or k in GENERIC_PAY:
                continue
            have.add(k)
            res.append({"term": term, "category": cat, "weight": weight, "pattern": None, "source": url, "reviewed": False,
                        "change_note": f"{TODAY}: {note} (실측 페이지 {n_page}쪽·사이트 {n_host}곳)"})
            need -= 1
            log[f"{cat} 채움"] += 1
    # 채우기 전에 공백만 다른 중복을 먼저 지운다 (채운 뒤 지우면 개수가 모자라진다)
    _u, _s = [], set()
    for x in res:
        k = (x["category"], re.sub(r"\s+", "", x["term"]))
        if k in _s:
            log["공백만 다른 중복 제거"] += 1
            continue
        _s.add(k)
        _u.append(x)
    res[:] = _u
    fill("gambling_core", mined["core"], 1.0, "실측 스팸에서 뽑은 도박 광고 복합어")
    fill("gambling_lure", [r for r in mined["lure"] if r[0].replace(" ", "") not in ("쿠폰", "환전", "충전", "보너스", "출석", "보증금")],
         0.6, "실측 스팸에서 뽑은 유인 문구")
    fill("gambling_lure", mined.get("lure2", []), 0.6, "실측 스팸에서 뽑은 유인 문구(입출금·보너스 꼴)")
    # 그래도 모자라면 한 사이트라도 2쪽 이상에 나온 것까지
    fill("gambling_lure", mined["lure"] + mined.get("lure2", []), 0.6, "실측 스팸에서 뽑은 유인 문구(한 사이트 여러 글)", min_host=1, min_page=2)
    fill("gambling_lure", mined["lure"] + mined.get("lure2", []), 0.6, "실측 스팸에서 뽑은 유인 문구(실측 1회)", min_host=1, min_page=1)

    # 공백만 다른 같은 어휘는 하나만 (원래 seed 에 있던 「무한 매충」/「무한매충」 등)
    uniq, seen_t = [], set()
    for x in res:
        k = (x["category"], re.sub(r"\s+", "", x["term"]))
        if k in seen_t:
            log["공백만 다른 중복 제거"] += 1
            continue
        seen_t.add(k)
        uniq.append(x)
    res = uniq
    Path(out).write_text(yaml.safe_dump(res, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
    with open(review, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["term", "category", "weight", "pattern", "source", "change_note", "검수(O/X)", "검수 메모"])
        for x in res:
            if not x.get("reviewed"):
                w.writerow([x["term"], x["category"], x["weight"], x.get("pattern") or "", x["source"], x.get("change_note", ""), "", ""])
    print(dict(log))
    print(len(res), Counter(x["category"] for x in res))
    print("reviewed", Counter(x.get("reviewed") for x in res))


if __name__ == "__main__":
    main(*sys.argv[1:6])
