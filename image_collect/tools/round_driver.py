"""추가 수집 차례 돌리기: 2026-11-07 00:00(KST)까지 씨앗 만들기 -> 수집 + OCR -> 집계를 되풀이한다.

사용: tools/resume_collect.sh (차례·씨앗 상태는 logs/driver_state.json 에 남아 이어 간다). 정지는 collect/PAUSE 파일을 만든다.
각 차례:
  (1) 도박 외 씨앗: 1차 dev_data 의 피해 도메인 게시판 목록에서 제목에 도박 외 낱말이 있는 글. 차례마다 더 뒤쪽 목록을 본다.
      적은 종류(invest, forgery, loan, adult, drug 순)를 먼저 뽑고, 차례당 도메인 PER_HOST 쪽, 누적 도메인 CAP 쪽까지.
      씨앗이 바닥나면 CAP 을 15쪽씩 CAP_MAX 까지 올린다. 업자 사이트로 보이는 도메인은 is_excluded 로 뺀다.
  (2) 일반 씨앗: 목표 종류 중 GEN_ENOUGH 장 미만이거나 도메인 15곳 미만인 종류만 GEN_POOL 에서 도메인을 더한다.
  (3) collect.py 3갈래(새 파일 번호) + ocr_run.py 4갈래를 함께 돌리고 모두 끝날 때까지 기다린다. 멈춘 뒤에도 고정 OCR 을 그대로 쓴다.
  (4) round_status.py 집계와 OCR 글 낱말 기준 도박 외 후보 수(logs/round_est.csv, 라벨 아님)를 적는다.
멈춤: 차례가 끝날 때마다 달성 기준(라벨 초안 기준)을 검사해 모두 채웠으면 멈춘다. 마감을 넘겼거나 logs/stop_request 가 있어도 멈춘다. 진행 중인 차례는 마친다. 씨앗이 CAP_MAX 에서도 두 차례 연속 0쪽이면 근거와 시각을 적고 멈춘다.
규칙: 다른 등록 도메인은 열지 않고 리디렉트를 따라가지 않으며 robots 를 지킨다(collect.py, make_seeds_add.fetch). 이미지를 만들거나 합성하지 않는다.
"""
import csv
import ctypes
import glob
import json
import os
import random
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from make_seeds_add import ROOT, already, anchors, fetch, is_excluded, reg, robots_ok, site_type_of  # noqa: E402
from make_seeds_shop2 import fetch_same  # noqa: E402
import safe_io  # noqa: E402

KST = timezone(timedelta(hours=9))
DEADLINE = datetime(2026, 11, 7, 0, 0, tzinfo=KST)
COL = os.path.join(ROOT, "collect")
LOG = os.path.join(ROOT, "logs")
PER_HOST, CAP, CAP_STEP, CAP_MAX = 6, 30, 15, 60
GEN_PER_ROUND, GEN_ENOUGH, GEN_DOMS = 10, 150, 5  # 일반은 기준(100장·5곳)에 여유를 둔 값까지만 더한다
TITLE = {  # 씨앗 고르기용 제목 낱말이다. 라벨은 그림을 보고 따로 붙인다
    "invest": r"리딩방|주식\s*리딩|코인\s*리딩|해외선물|선물\s*대여|선물옵션|수익\s*보장|원금\s*보장|고수익\s*투자|FX\s*마진|급등주|종목\s*추천|주식\s*정보방|비트코인\s*리딩|코인\s*방|USDT|테더|코인\s*환전|주식\s*방|투자\s*정보|재테크\s*방",
    "forgery": r"대리시험|대리\s*응시|대리출석|위조|졸업증명서|성적증명서|증명서\s*제작|학위증|면허증\s*(제작|판매|구매)|신분증\s*(제작|판매|구매)|여권\s*제작|토익\s*대리|자격증\s*(대행|제작|판매|구매)|논문\s*대필|서류\s*(제작|위조|대행)|재직증명서|진단서\s*(제작|발급)|졸업장|통장\s*사본|영문\s*증명|증명서|학력\s*(위조|제작|세탁)|제작\s*전문|서류\s*전문|주민등록|운전면허|토익|대리\s*(시험|출석|수강)|여권|사문서",
    "loan": r"내구제|작업대출|급전|일수|소액결제|휴대폰대출|신용불량|무직자대출|상품권\s*현금화|정보이용료|유심\s*개통|비대면대출|대출\s*상담|당일\s*대출",
    "adult": r"(?<!\d)060(?!\d)|폰팅|출장안마|출장\s*마사지|조건만남|오피\s*사이트|콜걸|성인\s*채팅|유흥|오피|홈타이|마사지\s*(출장|예약)|도우미|룸\s*싸롱|룸살롱|풀싸롱|노래방\s*알바|쓰리노|주대|전화\s*데이트|소개팅",
    "drug": r"비아그라|시알리스|레비트라|낙태약|미프진|정력제|필름형|발기부전|조루약|필로폰|대마초|졸피뎀|스테로이드\s*판매|약국\s*대행|구매\s*대행\s*약|흥분제|최음제|사정\s*지연|조루|미프지|약물\s*대행|사이트\s*정품",
    "etc": r"흥신소|심부름센터|계정\s*판매|통장\s*매입|대포통장|대포폰",
    "spam": r"텔레|텔그|카톡|라인\s*문의|24시간\s*상담|연중무휴",  # 종류를 안 밝힌 스팸 글. 위조·투자 배너는 제목에 낱말이 없을 때가 있다
}
TITLE = {k: re.compile(v, re.I) for k, v in TITLE.items()}
GAMBLE_TITLE = re.compile(r"토토|카지노|바카라|슬롯|홀덤|파워볼|먹튀|꽁머니|가입코드", re.I)
REQUIRED = ("invest", "forgery", "adult", "drug", "loan")


def needed():
    """라벨 초안에서 30장 미만인 종류. 모두 채웠으면 출처 쏠림을 줄이려고 전 종류와 도박 제목까지 받는다."""
    cat = Counter()
    for fn in ("labels_draft.csv", "labels_draft_add.csv"):
        for r in safe_io.read_csv(os.path.join(COL, fn)):
            if r["label"] == "illegal":
                cat[r["category"]] += 1
    need = [c for c in REQUIRED if cat[c] < 30]
    # 모자란 종류를 앞에 두고, 위조·투자 배너가 다른 스팸 글에 섞여 나오므로 나머지 스팸 글도 뒤에 받는다
    rest = ["loan", "adult", "drug", "etc"] if need == [] else []  # 종류 기준을 채웠으면 쏠림 조건을 위해 도박 외 전 종류를 받는다
    return need + ["spam"] + rest
GEN_POOL = {
    "news": ["kookje.co.kr", "busan.com", "imaeil.com", "kwnews.co.kr", "jjan.kr", "kado.net", "idomin.com", "gnnews.co.kr", "ksilbo.co.kr",
             "joongdo.co.kr", "daejonilbo.com", "kihoilbo.co.kr", "incheonilbo.com", "kyeonggi.com", "newspim.com", "edaily.co.kr", "fnnews.com",
             "mt.co.kr", "ajunews.com", "heraldcorp.com", "kmib.co.kr", "segye.com", "hankookilbo.com", "seoul.co.kr", "munhwa.com", "sbs.co.kr"],
    "shopping": ["10x10.co.kr", "dabagirl.co.kr", "naning9.com", "stylenanda.com", "attrangs.co.kr", "hotping.co.kr", "mixxmix.com", "jogunshop.com",
                 "lotteimall.com", "adidas.co.kr", "dyson.co.kr", "daisomall.co.kr", "hanssem.com", "iloom.com", "tworld.co.kr", "bookk.co.kr",
                 "hottracks.co.kr", "kyobolife.co.kr", "e-himart.co.kr", "onnuri.co.kr"],
    "finance": ["shinhancard.com", "bccard.com", "kbcard.com", "wooricard.com", "hanacard.co.kr", "meritzfire.com", "samsungfire.com", "hi.co.kr",
                "kyobo.co.kr", "truefriend.com", "nhqv.com", "kiwoom.com", "shinhansec.com", "kfb.or.kr", "fss.or.kr", "kinfa.or.kr", "kbanknow.com",
                "tossbank.com", "suhyup-bank.com", "jejubank.co.kr", "jbbank.co.kr", "kjbank.com"],
    "hospital": ["inha.com", "schmc.ac.kr", "kuh.ac.kr", "khmc.or.kr", "mizmedi.com", "ncc.re.kr", "nmc.or.kr", "wmc.or.kr", "gnah.co.kr", "dkuh.co.kr",
                 "jbuh.co.kr", "kosinmed.or.kr", "dcmc.co.kr", "paik.ac.kr", "hanyang.ac.kr", "ewha.ac.kr"],
    "public": ["jeju.go.kr", "jeonbuk.go.kr", "gyeongnam.go.kr", "gb.go.kr", "chungnam.go.kr", "chungbuk.go.kr", "gwd.go.kr", "jeonnam.go.kr", "ulsan.go.kr",
               "sejong.go.kr", "police.go.kr", "nts.go.kr", "mof.go.kr", "molit.go.kr", "me.go.kr", "mcst.go.kr", "mss.go.kr", "gov.kr"],
    "university": [], "community": [],
}
GEN_LINK_BAD = re.compile(r"login|logout|member|join|\.pdf$|\.hwp$|\.zip$|\.xlsx?$|download", re.I)


class Paused(Exception):
    pass


def check_pause():
    if safe_io.paused():
        raise Paused


def log(*a):
    line = datetime.now(KST).strftime("%m-%d %H:%M ") + " ".join(str(x) for x in a)
    print(line, flush=True)
    with open(os.path.join(LOG, "driver.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def title_cat(t):
    for c, rx in TITLE.items():
        if rx.search(t):
            return c
    return ""


def list_pages(url, a, b):
    """글 주소 -> 그 게시판 목록 a~b 쪽 주소. 모르는 형식이면 빈 목록."""
    u = urlparse(url)
    q = parse_qs(u.query)
    base = f"{u.scheme}://{u.netloc}"
    pages = range(a, b + 1)
    if "bo_table" in q:
        return [f"{base}{u.path}?bo_table={q['bo_table'][0]}&page={k}" for k in pages]
    if u.path.endswith("read.html") and "board_no" in q:
        return [f"{base}{u.path[:-9]}list.html?board_no={q['board_no'][0]}&page={k}" for k in pages]
    if u.path.endswith("view.php") and "bdId" in q:
        return [f"{base}{u.path[:-8]}list.php?bdId={q['bdId'][0]}&page={k}" for k in pages]
    m = re.match(r"^/article/[^/]+/(\d+)/", u.path)
    if m:
        return [f"{base}/board/product/list.html?board_no={m.group(1)}&page={k}" for k in pages]
    if "bmode" in q or ("idx" in q and "q" in q):  # imweb 게시판
        return [f"{base}{u.path}?page={k}" for k in pages]
    if q.get("mod", [""])[0] == "document" or "pageid" in q:  # KBoard
        return [f"{base}{u.path}?pageid={k}" for k in pages]
    if "document_srl" in q and "mid" in q:  # XE
        return [f"{base}{u.path}?mid={q['mid'][0]}&page={k}" for k in pages]
    return []


def board_key(url):
    u = urlparse(url)
    q = parse_qs(u.query)
    return u.path, q.get("bo_table", q.get("board_no", q.get("bdId", q.get("mid", [""]))))[0]


def host_pool():
    """피해 도메인 -> 게시판 글 주소 몇 개. dev_data 양성 페이지와 이미 연 페이지를 쓴다."""
    dev = json.load(open(os.path.join(LOG, "dev_source_domains.json"), encoding="utf-8"))
    pool = defaultdict(dict)
    for host, items in dev.items():
        h = host.split(":")[0]
        if is_excluded(h):
            continue
        for u, p, _ in items:
            if p and list_pages(u, 1, 1):
                pool[h].setdefault(board_key(u), u)
    for f in glob.glob(os.path.join(COL, "pages_*.csv")):
        for r in safe_io.read_csv(f):
            u = r["page_url"]
            h = urlparse(u).hostname or ""
            if r["status"] == "200" and not is_excluded(h) and list_pages(u, 1, 1) and r["site_type"] not in GEN_POOL:
                pool[h].setdefault(board_key(u), u)
    return pool


def opened_by_domain():
    c = Counter()
    for f in glob.glob(os.path.join(COL, "pages_*.csv")):
        for r in safe_io.read_csv(f):
            if r["origin"].split(":")[0] in ("board_list", "dev_nongamble"):
                c[r["site"]] += 1
    return c


def good_hosts():
    """도박 외 불법 라벨이 이미 나온 도메인. 이런 곳은 차례당 2배로 본다(같은 업자의 다른 그림이 나온다)."""
    good = set()
    lab = {r["file"] for r in safe_io.read_csv(os.path.join(COL, "labels_draft_add.csv")) if r["label"] == "illegal"}
    for r in safe_io.read_csv(os.path.join(COL, "labels_draft.csv")):
        if r["label"] == "illegal" and r["category"] != "gambling":
            lab.add(r["file"])
    for f in glob.glob(os.path.join(COL, "occurrences_*.csv")):
        for r in safe_io.read_csv(f):
            if os.path.basename(r["file"]) in lab:
                good.add(r["site"])
    return good


def heavy_sites():
    """불법 라벨 중 비중이 7% 이상인 사이트. 한 사이트 10% 이하 기준을 해치지 않게 씨앗에서 뺀다(파일은 지우지 않는다)."""
    lab = set()
    for fn in ("labels_draft.csv", "labels_draft_add.csv"):
        lab |= {r["file"] for r in safe_io.read_csv(os.path.join(COL, fn)) if r["label"] == "illegal"}
    by = defaultdict(set)
    for f in glob.glob(os.path.join(COL, "occurrences_*.csv")):
        for r in safe_io.read_csv(f):
            fn = os.path.basename(r["file"])
            if fn in lab:
                by[r["site"]].add(fn)
    n = len(lab) or 1
    return {s for s, v in by.items() if len(v) / n >= 0.07}


def build_ng(k, cap, state):
    rng = random.Random(k)
    done = already()
    opened = opened_by_domain()
    pool = host_pool()
    w = k - state.get("w0", 0)  # 제목 낱말을 넓히면 w0 을 옮겨 목록 앞쪽부터 다시 본다
    a, b = 3 * (w - 1) + 1, 3 * w
    rows, status = [], Counter()
    need = needed()
    good = good_hosts()
    heavy = heavy_sites()
    log(f"r{k} 씨앗에서 뺀 비중 큰 사이트 {sorted(heavy)}")
    log(f"r{k} 받을 종류 {need}")
    for h in sorted(pool):
        check_pause()
        d = reg("http://" + h)
        room = min(PER_HOST * (2 if d in good else 1), cap - opened[d])
        if d in heavy or room <= 0 or state["zero"].get(h, 0) >= 3:
            continue
        cats = defaultdict(list)
        boards = sorted(pool[h].items())[:3]
        for _, sample in boards:
            for lu in list_pages(sample, a, b):
                page, st = fetch(lu)
                status[st] += 1
                for u, t in (anchors(page, lu) if page else ()):
                    if reg(u) != d or u in done or u == lu or len(t) < 4:
                        continue
                    c = title_cat(t) or ("gambling" if GAMBLE_TITLE.search(t) else "")
                    if c in need and all(u != x for x in cats[c]) and robots_ok(u):
                        cats[c].append(u)
        n = sum(len(v) for v in cats.values())
        state["zero"][h] = 0 if n else state["zero"].get(h, 0) + 1
        pick = []
        for c in need:  # 적은 종류부터
            rng.shuffle(cats[c])
        while len(pick) < room and any(cats[c] for c in need):
            for c in need:
                if cats[c] and len(pick) < room:
                    pick.append((c, cats[c].pop()))
        rows += [dict(page_url=u, site_type=site_type_of(h, urlparse(u).path), origin=f"board_list:{c}") for c, u in pick]
    rng.shuffle(rows)
    log(f"r{k} 목록 받기 {dict(status)}, 도박 외 씨앗 {len(rows)}쪽 {dict(Counter(r['origin'] for r in rows))}, 도메인 {len({urlparse(r['page_url']).hostname for r in rows})}")
    return rows


def gen_counts():
    lab = {}
    for fn in ("labels_draft.csv", "labels_draft_add.csv"):
        p = os.path.join(COL, fn)
        if os.path.exists(p):
            lab.update({r["file"]: r["label"] for r in safe_io.read_csv(p)})
    first, doms = {}, defaultdict(set)
    for f in glob.glob(os.path.join(COL, "occurrences_*.csv")):
        for r in safe_io.read_csv(f):
            fn = os.path.basename(r["file"])
            if lab.get(fn, "other") == "other":
                first.setdefault(fn, r["site_type"])
                doms[r["site_type"]].add(r["site"])
    return Counter(first.values()), doms


def build_gen(k, state):
    rng = random.Random(1000 + k)
    done = already()
    counts, doms = gen_counts()
    rows = []
    for kind, pool in GEN_POOL.items():
        if counts[kind] >= GEN_ENOUGH and len(doms[kind]) >= GEN_DOMS:
            continue
        used = state["gen_used"].setdefault(kind, [])
        for d in [x for x in pool if x not in used][:GEN_PER_ROUND]:
            check_pause()
            used.append(d)
            page, st, final = fetch_same(f"https://www.{d}/", d)
            if not page and not st.startswith("offsite"):
                page, st, final = fetch_same(f"https://{d}/", d)
            if not page:
                log(f"r{k} 일반 {kind} {d} 건너뜀: {st}")
                continue
            links = sorted({u.split("#")[0] for u, _ in anchors(page, final)
                            if reg(u) == d and urlparse(u).scheme in ("http", "https") and len(urlparse(u).path) > 1 and not GEN_LINK_BAD.search(u)})
            links = [u for u in links if u not in done and robots_ok(u)]
            if final not in done:
                rows.append(dict(page_url=final, site_type=kind, origin=f"gen_r{k}"))
            rows += [dict(page_url=u, site_type=kind, origin=f"gen_r{k}") for u in rng.sample(links, min(4, len(links)))]
    log(f"r{k} 일반 씨앗 {len(rows)}쪽 {dict(Counter(r['site_type'] for r in rows))}, 현재 {dict(counts)}")
    return rows


def write_seeds(name, rows):
    p = os.path.join(ROOT, name)
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["page_url", "site_type", "origin"])
        w.writeheader()
        w.writerows(rows)
    return p


def estimate(k):
    """OCR 글 낱말 기준 도박 외 후보 수. 라벨이 아니라 차례별 수확을 가늠하는 값이다."""
    seen = 0
    c = Counter()
    for f in glob.glob(os.path.join(COL, "ocr_raw*.csv")):
        for r in safe_io.read_csv(f):
            seen += 1
            t = title_cat(r["text"]) or title_cat(r["text"].replace(" ", ""))
            if t:
                c[t] += 1
    p = os.path.join(LOG, "round_est.csv")
    new = not os.path.exists(p)
    with open(p, "a", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["round", "ocr_read", *TITLE])
        w.writerow([k, seen, *[c[x] for x in TITLE]])
    log(f"r{k} OCR 읽은 파일 {seen}, 낱말 기준 도박 외 후보 {dict(c)}")


def run_round(k, p, py, env):
    procs = []
    for i in range(3):
        lf = open(os.path.join(LOG, f"crawl_r{k}_{i}.log"), "a", encoding="utf-8")
        procs.append(subprocess.Popen([py, "-W", "ignore", os.path.join(HERE, "collect.py"), "--seeds", p, "--out", COL, "--shard", str(i), "--nshards", "3",
                                       "--file-shard", str(100 + k * 10 + i)], stdout=lf, stderr=subprocess.STDOUT, env=env))
    for i in range(4):
        lf = open(os.path.join(LOG, f"ocr_r{k}_{i}.log"), "a", encoding="utf-8")
        procs.append(subprocess.Popen([py, "-W", "ignore", os.path.join(HERE, "ocr_run.py"), str(i), "4"], stdout=lf, stderr=subprocess.STDOUT, env=env))
    for pr in procs:
        pr.wait()
    return [pr.returncode for pr in procs]


def leftovers():
    """r2: 앞서 끊은 1차 씨앗의 남은 페이지와 금융·병원·공공 씨앗. 목록 받기 없이 바로 수집한다."""
    done = already()
    rows = []
    for name in ("seeds_gen2.csv", "seeds_nongamble.csv", "seeds_gen3.csv"):
        rows += [r for r in safe_io.read_csv(os.path.join(ROOT, name)) if r["page_url"] not in done]
    return rows


def main():
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)  # 이 프로세스가 도는 동안 절전 진입을 막는다
    pflag = os.path.join(LOG, "driver_paused")
    if safe_io.paused():
        log("collect/PAUSE 가 있어 시작하지 않는다.")
        return
    if os.path.exists(pflag):
        os.remove(pflag)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    sp = os.path.join(LOG, "driver_state.json")
    state = {"zero": {}, "gen_used": {}, "cap": CAP, "empty": 0, "k": 2, "active": 0}
    if os.path.exists(sp):
        try:
            state.update(json.load(open(sp, encoding="utf-8")))
        except ValueError:
            log("driver_state.json 을 읽지 못해 기본값으로 이어 간다(이미 연 페이지는 pages_*.csv 로 건너뛴다).")
    py = sys.executable

    def save():
        tmp = sp + ".tmp"
        json.dump(state, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
        os.replace(tmp, sp)

    def should_stop(tag):
        """달성 기준을 라벨 초안 기준으로 검사한다. logs/stop_request 가 있어도 멈춘다."""
        out = subprocess.run([py, "-W", "ignore", os.path.join(HERE, "round_status.py"), tag], capture_output=True, text=True, encoding="utf-8", env=env).stdout
        log(out)
        if os.path.exists(os.path.join(LOG, "stop_request")):
            log("stop_request 파일이 있어 멈춘다.")
            return True
        if json.load(open(os.path.join(LOG, "criteria.json"), encoding="utf-8"))["met"]:
            log("달성 기준을 라벨 초안 기준으로 모두 채워 멈춘다.")
            return True
        return False

    try:
        while datetime.now(KST) < DEADLINE:
            k = state["k"]
            check_pause()
            p = os.path.join(ROOT, f"seeds_r{k}.csv")
            if state.get("active") != k:  # 씨앗을 아직 안 만든 차례. 만든 차례를 이어 갈 때는 같은 씨앗을 쓴다
                if should_stop(f"r{k}_start"):
                    break
                log(f"r{k} 시작, CAP {state['cap']}")
                if k == 2:
                    rows = leftovers()
                else:
                    ng = build_ng(k, state["cap"], state)
                    gen = build_gen(k, state)
                    rows = ng + gen
                save()
                if not rows:
                    if state["cap"] < CAP_MAX:
                        state["cap"] += CAP_STEP
                        log(f"r{k} 씨앗 0쪽, CAP 을 {state['cap']} 로 올림")
                    else:
                        state["empty"] += 1
                        log(f"r{k} CAP {CAP_MAX} 에서 씨앗 0쪽 ({state['empty']}회째)")
                        if state["empty"] >= 2:
                            log("씨앗 바닥: 두 차례 연속 도박 외·일반 씨앗 0쪽. 멈춘다.")
                            break
                    state["k"] = k + 1
                    save()
                    continue
                state["empty"] = 0
                random.Random(k).shuffle(rows)
                p = write_seeds(f"seeds_r{k}.csv", rows)
                state["active"] = k
                save()
            else:
                log(f"r{k} 이어 가기")
            codes = run_round(k, p, py, env)
            log(f"r{k} 수집·OCR 프로세스 끝, 종료 코드 {codes}")
            check_pause()
            estimate(k)
            state["k"] = k + 1
            state["active"] = 0
            save()
            time.sleep(5)
    except Paused:
        save()
        log(f"collect/PAUSE: 일시 정지. 재개는 tools/resume_collect.sh (r{state['k']}, 씨앗 만든 차례 {state.get('active')})")
        open(pflag, "w").write(datetime.now(KST).isoformat())
        return
    log("드라이버 끝")
    open(os.path.join(LOG, "driver_done"), "w").write(datetime.now(KST).isoformat())


if __name__ == "__main__":
    main()
