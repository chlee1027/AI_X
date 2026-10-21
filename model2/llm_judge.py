"""API 판: 애매한 후보만 언어 모델에 2차 판정을 묻는다 (10-19, 진행보고서 7-30절).

근거: 독립·진단 사이트에서 놓친 광고는 거의 모두 「숨김·위장 규칙은 켜졌는데 광고 점수가 문턱 아래」였다(7-18·7-25·7-26절).
글자 조각을 외우는 판정기는 처음 보는 문체에 약하고, 뜻을 읽는 언어 모델은 그 약점을 정면으로 겨냥한다.

설계:
  - 묻는 대상: 숨김·위장 규칙이 켜진 후보 중 광고 점수가 [LO, 문턱 + BAND) 인 것(애매한 구간). 그보다 높으면 그대로 검출,
    낮으면 그대로 버림. 문턱 위 애매한 것도 묻는 까닭: 정상 공공 사이트 메뉴(예: 「온라인지로」 0.66)가 문턱 바로 위에서 오탐이 된다.
  - 판정: 언어 모델이 「광고」라 하면 점수를 0.99, 「정상」이라 하면 0.0 으로 바꾼다(mode "both"). mode "promote" 는 문턱 아래만
    묻고 「광고」일 때만 올린다(잘못된 「정상」 판정으로 재현을 잃을 위험이 없음). 어느 쪽을 쓸지는 llm_eval.py(개발 데이터·공공기관)로 정한다.
  - 같은 글자는 한 번만 묻는다(메뉴가 쪽마다 반복). 한 검사에서 최대 MAX_ITEMS 개, 한 번에 BATCH 개씩.
  - 실패하면(키 없음·인터넷 없음·오류·시간 초과) 그 뒤로는 묻지 않고 API 없는 판과 똑같이 낸다. 0점 위험이 없다.
  - 표준 라이브러리(urllib)만 쓴다. 실행 파일에 따로 묶을 패키지가 없다.
  - 키: 환경변수 ANTHROPIC_API_KEY, 없으면 실행 파일 옆 api_key.txt. 키는 코드·결과 파일에 남기지 않는다.
프롬프트는 일반 원칙으로 쓴 것이고 팀원·독립 사이트의 정답이나 문구를 보고 쓴 것이 아니다.
"""
import json
import os
import re
import time
import urllib.request
from pathlib import Path

from textfeat import restore

MODEL = os.environ.get("ADDETECTOR_LLM_MODEL", "claude-haiku-5-5")
LO, BAND = 0.03, 0.25
MAX_ITEMS, BATCH = 800, 30
TIMEOUT, BUDGET_SEC = 40, 8 * 60  # 호출 하나 40초, 한 검사에서 API 에 쓰는 시간 최대 8분(30분 상한 안)

SYSTEM = """너는 공공기관 웹사이트 점검 도구의 2차 판정기다.
각 항목은 웹페이지에서 화면에 보이지 않게 숨겨졌거나 글자가 위장된(자모를 풀어 쓰거나 닮은꼴 문자로 바꾼) 요소의 글이다.
숨겨져 있다는 사실만으로는 광고가 아니다. 정상 사이트도 메뉴, 접힌 목록, 화면 낭독기용 안내, 건너뛰기 링크를 숨긴다.

판정 기준:
- ad: 불법·유해 광고를 홍보하거나 이용을 유도하는 글. 예: 도박·카지노·토토, 성매매·유흥업소, 불법 대출·카드깡·소액결제 현금화,
  마약 판매, 처방 없는 의약품 판매, 투자 리딩방·원금 보장 투자, 대포통장·위조 문서, 그리고 그런 업체의 이름·주소·연락처만 있는 글.
- normal: 사이트 본래 내용. 예: 메뉴·바로가기, 기관·부서 이름, 공지·보도자료, 민원 안내, 다른 기관 링크, 단속·예방 캠페인(마약 예방, 도박 중독 상담 등).
위장된 글자는 풀어서 읽어라. 확실하지 않으면 normal 이다.
반드시 JSON 배열만 출력한다: [{"id": 번호, "ad": true 또는 false}, ...]"""


def _env_file(p):
    """.env 한 파일에서 ANTHROPIC_API_KEY 값을 읽는다(KEY=값, 따옴표·export·주석 허용)."""
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[7:].strip()
        if line.startswith("ANTHROPIC_API_KEY") and "=" in line:
            v = line.split("=", 1)[1].split(" #")[0].strip().strip('"').strip("'")
            if v:
                return v
    return ""


def _key():
    """키 찾는 순서: 환경변수 ANTHROPIC_API_KEY -> 실행 파일 옆 .env -> (예전 방식) api_key.txt.
    10-20(진행보고서 7-50절): 모집요강 붙임3, 키는 소스와 분리한 .env 에서 실행 시점에 읽고 재빌드 없이 교체할 수 있어야 한다."""
    k = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    bases = (Path(os.environ.get("ADDETECTOR_HOME", ".")), Path.cwd())
    for name in (".env", "api_key.txt"):
        for base in bases:
            p = base / name
            if not k and p.exists():
                k = _env_file(p) if name == ".env" else p.read_text(encoding="utf-8-sig").strip()
    return k


class Judge:
    def __init__(self, key=None, log=print, mode=None):
        # mode: "both" = 광고면 올리고 정상이면 내림 / "promote" = 광고면 올리기만(문턱 위 후보는 묻지 않음, 재현 손실 없음)
        #       / "demote" = 문턱 위 애매한 것만 묻고 정상이면 내리기만(10-20, 7-44절. new1 에서 올리기가 오탐을 늘림)
        self.mode = mode or os.environ.get("ADDETECTOR_API_MODE", "demote")  # 7-32절 both -> 10-20 v9 에서 demote(7-45절)
        self.key = key if key is not None else _key()
        self.cache, self.calls, self.asked, self.spent = {}, 0, 0, 0.0
        self.dead = None if self.key else "API 키 없음"
        self.log = log
        self.usage = {"input_tokens": 0, "output_tokens": 0}
        self.missing, self.truncated = 0, 0

    def _ask(self, items):
        body = {"model": MODEL, "max_tokens": 1024 + 48 * len(items), "system": SYSTEM,
                "messages": [{"role": "user", "content": json.dumps(items, ensure_ascii=False)}]}
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode("utf-8"),
                                     headers={"x-api-key": self.key, "anthropic-version": "2023-06-01",
                                              "content-type": "application/json"})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            out = json.loads(r.read().decode("utf-8"))
        self.spent += time.time() - t0
        self.calls += 1
        for k in self.usage:
            self.usage[k] += out.get("usage", {}).get(k, 0)
        text = "".join(c.get("text", "") for c in out.get("content", []) if c.get("type") == "text")
        # 10-19(7-32절): 모델이 답 앞에 생각 토큰을 써서 출력 상한에 걸리면 배열이 잘린다. 배열 통째로 읽으면 한 묶음이
        # 통째로 버려지므로 항목 하나씩 읽고, 못 받은 항목 수를 센다(조용히 사라지지 않게).
        got = {int(i): v == "true" for i, v in re.findall(r'"id"\s*:\s*(\d+)\s*,\s*"ad"\s*:\s*(true|false)', text)}
        self.missing += len(items) - len(got)
        if out.get("stop_reason") == "max_tokens":
            self.truncated += 1
        return got

    def verdicts(self, texts):
        """texts: 위장을 푼 글자 목록 -> {글자: True(광고)/False(정상)} (못 물은 것은 빠짐)"""
        todo = [t for t in dict.fromkeys(texts) if t not in self.cache]
        todo = todo[:max(0, MAX_ITEMS - self.asked)]
        for i in range(0, len(todo), BATCH):
            if self.dead:
                break
            if self.spent > BUDGET_SEC:
                self.dead = "API 시간 예산 다 씀"
                break
            chunk = todo[i:i + BATCH]
            try:
                got = self._ask([{"id": j, "text": t[:300]} for j, t in enumerate(chunk)])
            except Exception as e:
                self.dead = f"API 실패: {type(e).__name__}"
                self.log(f"[API] {self.dead}, 이후는 API 없이 판정합니다")
                break
            self.asked += len(chunk)
            for j, t in enumerate(chunk):
                if j in got:
                    self.cache[t] = got[j]
        return {t: self.cache[t] for t in texts if t in self.cache}

    def adjust(self, rows, ad, thr):
        """rows 의 광고 점수 ad(배열)를 고쳐 돌려준다. 고친 줄에는 r['_llm'] = 'ad' 또는 'normal' 을 단다."""
        if self.dead:
            return ad
        ad = list(ad)
        ask = []
        for k, r in enumerate(rows):
            ts = list(r.get("rt") or {})
            if not ts:
                continue
            hi = max(thr[t] for t in ts) + (BAND if self.mode in ("both", "demote") else 0.0)
            lo = min(thr[t] for t in ts) if self.mode == "demote" else LO  # 10-20 demote: 문턱 위 애매한 것만 묻는다(7-44절)
            if lo <= ad[k] < hi:
                ask.append((ad[k], k))
        ask.sort(reverse=True)  # 문턱에 가까운 것부터
        texts = {k: restore(rows[k]["text"]).strip() for _, k in ask}
        v = self.verdicts([texts[k] for _, k in ask if texts[k]])
        for _, k in ask:
            if texts[k] in v:
                if self.mode == "promote" and not v[texts[k]]:
                    continue
                if self.mode == "demote" and v[texts[k]]:  # 내리기만: 「광고」면 점수를 그대로 둔다
                    rows[k]["_llm"] = "ad"
                    continue
                ad[k] = 0.99 if v[texts[k]] else 0.0
                rows[k]["_llm"] = "ad" if v[texts[k]] else "normal"
        return ad

    def summary(self):
        return {"model": MODEL, "mode": self.mode, "calls": self.calls, "asked": self.asked, "seconds": round(self.spent, 1),
                "usage": dict(self.usage), "missing": self.missing, "truncated": self.truncated, "fallback": self.dead}


# ---------------------------------------------------------------------------------------------------------------------
# 10-21 API v2 (진행보고서 7-65절). 사용자: 「API 를 쓸 거면 확실하게 잡았으면 좋겠다」. 지금 판(v1)은 글만 보고, 「확실하지 않으면
# normal」로 기울고, 확신 정도 없이 답을 그대로 따른다. v2 는 (1) 숨김·위장 방식과 링크 주소를 함께 주고, (2) 「공공기관 사이트에
# 숨겨 넣은 홍보 글」이라는 맥락으로 묻고, (3) 확신(sure)이 있을 때만 점수를 바꾼다. 프롬프트는 일반 원칙으로 썼다(new1·진단 사이트
# 정답이나 글을 보고 쓰지 않음).
SYSTEM2 = """너는 공공기관 웹사이트 보안 점검 도구의 2차 판정기다.
각 항목은 공공기관 사이트에서 화면에 보이지 않게 숨겨졌거나 글자가 위장된 요소다. 글(text), 숨김·위장 방식(how), 링크가 있으면 그 주소(link)가 주어진다.
공공기관 사이트에 상업적 홍보 글이 숨겨져 있다면 누군가 몰래 끼워 넣은 스팸 광고다. 다만 숨김 자체는 정상 사이트에도 흔하다(접힌 메뉴, 화면 낭독기 안내, 건너뛰기 링크).

ad=true: 상품·서비스·업체·사이트를 홍보하거나 가입·접속·구매·연락을 유도하는 글. 도박·카지노·토토, 성인·유흥, 불법 대출·현금화, 의약품 판매,
  투자 리딩, 각종 대행·업체 홍보, 업체 이름·도메인·연락처(메신저 아이디·전화)만 나열한 글, 그런 곳으로 가는 링크 글.
ad=false: 기관 본래 내용. 메뉴·바로가기, 기관·부서 이름, 공지·보도자료, 민원·서비스 안내, 다른 공공기관·공익 단체 링크, 화면 낭독기 안내,
  예방·단속·상담 캠페인(도박 중독 상담 등), 글자가 깨져 읽을 수 없는 글.
위장된 글자(자모 분해, 닮은꼴 문자, 기호로 끊은 글)는 풀어서 읽어라.
sure=true: 판단이 확실할 때. 글이 너무 짧거나 문맥이 부족해 반반이면 sure=false 로 답하라(이때 ad 값은 참고로만 쓴다).
반드시 JSON 배열만 출력한다: [{"id": 번호, "ad": true 또는 false, "sure": true 또는 false}, ...]"""


def _ext_link(r):
    """다른 호스트로 가는 http 링크이고 글이 8자 이상인가(v2x 가 더 묻는 대상)."""
    from urllib.parse import urlparse
    h = r.get("href") or ""
    if not h.startswith("http") or len((r.get("text") or "").strip()) < 8:
        return False
    a, b = urlparse(h).hostname or "", urlparse(r.get("url") or "").hostname or ""
    return bool(a) and a.removeprefix("www.") != b.removeprefix("www.")


SYSTEM3 = """너는 공공기관 웹사이트 보안 점검 도구의 최종 판정기다. 1차 판정에서 확신하지 못한 요소만 온다.
각 항목: 숨겨졌거나 글자가 위장된 요소의 글(text), 숨김·위장 방식(how), 링크 주소(link), 링크가 사이트 밖 도메인인지(external),
쪽 제목(page_title), 요소가 놓인 위치(area: 본문 / 메뉴·머리말·꼬리말), 같은 부모 안의 보이는 앞뒤 글(around).

판단 기준: 공공기관이 이 글을 일부러 숨길 정상적인 까닭이 있는가?
- 정상 까닭: 메뉴·하위 메뉴·탭·드롭다운, 화면 낭독기용 안내(「본문 바로가기」 등), 슬라이드·배너 넘김 장치, 기관·부서·관련 기관 이름, 쪽 내용과 이어지는 설명.
- 그런 까닭 없이, 본문에 숨겨진 채 쪽 내용과 상관없는 혜택·가입·상담·접수·적립·코드 입력 같은 유도 문구이거나 사이트 밖 도메인으로 보내면,
  누군가 끼워 넣은 홍보(광고)다. 광고 낱말(도박·성인 등)이 없어도 홍보일 수 있다.
위장된 글자는 풀어서 읽어라. 판단이 확실하면 sure=true, 그래도 반반이면 sure=false.
반드시 JSON 배열만 출력한다: [{"id": 번호, "ad": true 또는 false, "sure": true 또는 false}, ...]"""
NAVY = re.compile(r"\b(nav|gnb|lnb|snb|menu|header|footer|util|skip|breadcrumb|sitemap|quick)", re.I)


def _context(r, by_key):
    """재질문 맥락: 위치(본문/메뉴·머리말·꼬리말), 부모의 보이는 앞뒤 글, 외부 링크 여부. 10-21(진행보고서 7-80절)."""
    from urllib.parse import urlparse
    area, p, around = "본문", r.get("parent", -1), ""
    if NAVY.search(r.get("sel") or ""):
        area = "메뉴·머리말·꼬리말"
    hops = 0
    while p is not None and p >= 0 and hops < 12:
        a = by_key.get((r["sid"], p))
        if a is None:
            break
        if a.get("tag") in ("nav", "header", "footer") or NAVY.search(a.get("sel") or ""):
            area = "메뉴·머리말·꼬리말"
        if not around and a.get("text"):
            t = a["text"].replace(r["text"], " ").strip()
            around = re.sub(r"\s+", " ", t)[:150]
        p, hops = a.get("parent", -1), hops + 1
    h = r.get("href") or ""
    ext = bool(h.startswith("http") and (urlparse(h).hostname or "").removeprefix("www.") != (urlparse(r.get("url") or "").hostname or "").removeprefix("www."))
    return {"area": area, "around": around, "external": ext, "page_title": r.get("ptitle", "")}


class Judge2(Judge):
    """v2: 맥락을 주고 확신이 있을 때만 바꾼다. mode 는 "v2"(올리기·내리기 둘 다, 확신 있을 때만)."""

    def __init__(self, key=None, log=print, model=None, wide=None, recheck=None, model2=None):
        super().__init__(key=key, log=log, mode="v2")
        # 10-21 v2r(진행보고서 7-80절): 「확신 없음」만 맥락을 더해 더 정확한 모델에 한 번 더 묻는다
        self.recheck = os.environ.get("ADDETECTOR_API_RECHECK", "0") == "1" if recheck is None else recheck
        self.model2 = model2 or os.environ.get("ADDETECTOR_LLM_MODEL2", "claude-sonnet-5-5")
        self.rechecked, self.recheck_sure, self.cache2 = 0, 0, {}
        # 10-21 v2x(진행보고서 7-73절): 점수가 LO 아래여도 숨김·위장 규칙에 걸린 외부 링크 글(8자 이상)은 묻는다
        self.wide = os.environ.get("ADDETECTOR_API_WIDE", "0") == "1" if wide is None else wide
        self.model = model or os.environ.get("ADDETECTOR_LLM_MODEL", MODEL)
        self.unsure = 0

    def _ask2(self, items):
        # 10-21(7-70절): 8831 에서 30개 묶음 하나가 출력 상한에 잘려 3개를 못 받았다 -> 상한을 넉넉히
        body = {"model": self.model, "max_tokens": 2048 + 128 * len(items), "system": SYSTEM2,
                "messages": [{"role": "user", "content": json.dumps(items, ensure_ascii=False)}]}
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode("utf-8"),
                                     headers={"x-api-key": self.key, "anthropic-version": "2023-06-01",
                                              "content-type": "application/json"})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=TIMEOUT * 2) as r:
            out = json.loads(r.read().decode("utf-8"))
        self.spent += time.time() - t0
        self.calls += 1
        for k in self.usage:
            self.usage[k] += out.get("usage", {}).get(k, 0)
        text = "".join(c.get("text", "") for c in out.get("content", []) if c.get("type") == "text")
        got = {int(i): (a == "true", s == "true") for i, a, s in
               re.findall(r'"id"\s*:\s*(\d+)\s*,\s*"ad"\s*:\s*(true|false)\s*,\s*"sure"\s*:\s*(true|false)', text)}
        self.missing += len(items) - len(got)
        if out.get("stop_reason") == "max_tokens":
            self.truncated += 1
        return got

    def verdicts2(self, items):
        """items: [{"key", "text", "how", "link"}] -> {key: (광고 여부, 확신)}"""
        todo = [it for it in {it["key"]: it for it in items}.values() if it["key"] not in self.cache]
        todo = todo[:max(0, MAX_ITEMS - self.asked)]
        for i in range(0, len(todo), BATCH):
            if self.dead:
                break
            if self.spent > BUDGET_SEC:
                self.dead = "API 시간 예산 다 씀"
                break
            chunk = todo[i:i + BATCH]
            payload = [{"id": j, "text": it["text"][:300], "how": it["how"], **({"link": it["link"]} if it["link"] else {})}
                       for j, it in enumerate(chunk)]
            # 10-21(진행보고서 7-74절): 시간 초과 한 번으로 그 검사의 API 가 통째로 꺼졌다(8831·8832 동시 실행에서 재현).
            # 묶음마다 2초·5초 쉬고 두 번 더 해 보고, 그래도 안 되면 그 묶음만 건너뛴다. 연속 3 묶음이 실패하면 끈다.
            got, err = None, None
            for wait in (0, 2, 5):
                if wait:
                    time.sleep(wait)
                try:
                    got = self._ask2(payload)
                    break
                except Exception as e:
                    err = e
                    self.retries = getattr(self, "retries", 0) + 1
            if got is None:
                self.fails = getattr(self, "fails", 0) + 1
                if self.fails >= 3:
                    self.dead = f"API 실패: {type(err).__name__}"
                    self.log(f"[API] {self.dead}(3 묶음 연속), 이후는 API 없이 판정합니다")
                    break
                continue
            self.fails = 0
            self.asked += len(chunk)
            for j, it in enumerate(chunk):
                if j in got:
                    self.cache[it["key"]] = got[j]
        return {it["key"]: self.cache[it["key"]] for it in items if it["key"] in self.cache}

    def _ask3(self, items):
        body = {"model": self.model2, "max_tokens": 2048 + 160 * len(items), "system": SYSTEM3,
                "messages": [{"role": "user", "content": json.dumps(items, ensure_ascii=False)}]}
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=json.dumps(body).encode("utf-8"),
                                     headers={"x-api-key": self.key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        t0 = time.time()
        with urllib.request.urlopen(req, timeout=TIMEOUT * 3) as r:
            out = json.loads(r.read().decode("utf-8"))
        self.spent += time.time() - t0
        self.calls += 1
        for k in self.usage:
            self.usage[k] += out.get("usage", {}).get(k, 0)
        text = "".join(c.get("text", "") for c in out.get("content", []) if c.get("type") == "text")
        got = {int(i): (a == "true", s_ == "true") for i, a, s_ in
               re.findall(r'"id"\s*:\s*(\d+)\s*,\s*"ad"\s*:\s*(true|false)\s*,\s*"sure"\s*:\s*(true|false)', text)}
        self.missing += len(items) - len(got)
        if out.get("stop_reason") == "max_tokens":
            self.truncated += 1
        return got

    def recheck_items(self, items):
        """items: [{"key", "text", "how", "link", 맥락...}] -> {key: (광고, 확신)}. 10개 묶음, 실패하면 그 묶음만 건너뛴다."""
        todo = [it for it in {it["key"]: it for it in items}.values() if it["key"] not in self.cache2]
        for i in range(0, len(todo), 10):
            if self.dead or self.spent > BUDGET_SEC:
                break
            chunk = todo[i:i + 10]
            payload = [{"id": j, "text": it["text"][:300], "how": it["how"], "link": it["link"], "external": it["external"],
                        "page_title": it["page_title"], "area": it["area"], "around": it["around"]} for j, it in enumerate(chunk)]
            got = None
            for wait in (0, 3):
                if wait:
                    time.sleep(wait)
                try:
                    got = self._ask3(payload)
                    break
                except Exception:
                    self.retries = getattr(self, "retries", 0) + 1
            if got is None:
                continue
            self.rechecked += len(chunk)
            for j, it in enumerate(chunk):
                if j in got:
                    self.cache2[it["key"]] = got[j]
        return {it["key"]: self.cache2[it["key"]] for it in items if it["key"] in self.cache2}

    def adjust(self, rows, ad, thr):
        if self.dead:
            return ad
        ad = list(ad)
        ask = []
        for k, r in enumerate(rows):
            ts = list(r.get("rt") or {})
            if ts and (LO <= ad[k] < max(thr[t] for t in ts) + BAND or (self.wide and ad[k] < LO and _ext_link(r))):
                how = "; ".join(f"{t}: {', '.join(w[:3])}" for t, w in (r.get("rt") or {}).items())[:200]
                text = restore(r["text"]).strip()
                if text:
                    ask.append((k, {"key": text + "\x00" + how, "text": text, "how": how, "link": (r.get("href") or "")[:120]}))
        v = self.verdicts2([it for _, it in ask])
        unsure = []
        for k, it in ask:
            if it["key"] in v:
                is_ad, sure = v[it["key"]]
                if not sure:
                    self.unsure += 1
                    rows[k]["_llm"] = "unsure"
                    unsure.append((k, it))
                    continue
                ad[k] = 0.99 if is_ad else 0.0
                rows[k]["_llm"] = "ad" if is_ad else "normal"
        if self.recheck and unsure and not self.dead:
            by_key = {(r["sid"], r["i"]): r for r in rows}
            items = []
            for k, it in unsure:
                ctx = _context(rows[k], by_key)
                items.append((k, dict(it, key=it["key"] + "|" + ctx["area"] + "|" + ctx["around"][:60], **ctx)))
            v2 = self.recheck_items([it for _, it in items])
            for k, it in items:
                if it["key"] in v2:
                    is_ad, sure = v2[it["key"]]
                    if sure:
                        self.recheck_sure += 1
                        ad[k] = 0.99 if is_ad else 0.0
                        rows[k]["_llm"] = ("ad" if is_ad else "normal") + "(재질문)"
        return ad

    def summary(self):
        s = super().summary()
        s.update(model=self.model, mode=("v2x" if self.wide else "v2") + ("+r" if self.recheck else ""), unsure=self.unsure,
                 retries=getattr(self, "retries", 0), rechecked=self.rechecked, recheck_sure=self.recheck_sure,
                 model2=self.model2 if self.recheck else None)
        return s
