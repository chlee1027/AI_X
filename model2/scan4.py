"""scan3.py(v3 동결본) 사본. v4 모델(train4.AdModel4)·v4 규칙(rules4.use())·v4 특징 추출(render4.PAGE_JS4)을 쓰게 한 것 말고는 scan3 과 같다.

사용: python scan4.py --url <진입 URL> --run runs/v4 --out scans/<이름> --report hedge [--max-pages 60 --minutes 10 --delay 1]
"""
import argparse
import hashlib
import json
import os
import pickle
import queue
import sys
import threading
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from pathlib import Path

from urllib.parse import urlparse

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "8")
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "model")]
import train2  # noqa: E402,F401
import train4  # noqa: E402,F401  (v4 모델을 불러오려면 필요)
import rules4  # noqa: E402

rules4.use()  # v4 규칙(학습 때와 같은 기본값)
from render4 import PAGE_JS4 as PAGE_JS  # noqa: E402  v4 숨김 특징 넷을 더한 추출(check_css.py)
from train2 import rule_cache  # noqa: E402
from admodel7 import ui_skip  # noqa: E402  (10-18: v7c 는 규칙 뒤에 UI 거르개를 씌운다. 진행보고서 7-19절)
from report import relocate, MODES  # noqa: E402
import extra as extra_mod  # noqa: E402  10-20 추가 유형(result_extra.json, 진행보고서 7-50절)
from site_scan import MAX_CAND, norm  # noqa: E402  (PAGE_JS 는 위에서 render4 것을 쓴다)
from common import MAIN4  # noqa: E402

SKIP_EXT = (".pdf", ".hwp", ".hwpx", ".zip", ".jpg", ".png", ".gif", ".xlsx", ".xls", ".doc", ".docx", ".ppt", ".pptx", ".mp4")


class Robots:
    """RFC 9309 robots.txt 판정. 10-17: urllib.robotparser 는 처음 맞는 규칙을 따르고 `$` 를 몰라
    「Disallow: /」 다음 「Allow: /$」 가 있는 사이트(국방부)의 첫 화면까지 금지로 봤다. 표준은 가장 긴(구체적인) 규칙이 이기고,
    길이가 같으면 허용이다. 그룹은 우리 이름이 따로 없으므로 `*` 그룹만 본다."""

    def __init__(self, text):
        import re
        self.rules, grp, cur_any, in_rules = [], [], False, False
        for line in text.splitlines():
            line = line.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            k, v = (x.strip() for x in line.split(":", 1))
            k = k.lower()
            if k == "user-agent":
                if in_rules:  # 새 그룹 시작
                    cur_any, in_rules = False, False
                cur_any = cur_any or v == "*"
            elif k in ("allow", "disallow"):
                in_rules = True
                if cur_any and v:
                    pat = re.escape(v).replace(r"\*", ".*")
                    if pat.endswith(r"\$"):
                        pat = pat[:-2] + "$"
                    self.rules.append((len(v), k == "allow", re.compile(pat)))

    def can_fetch(self, url):
        from urllib.parse import urlsplit
        u = urlsplit(url)
        path = (u.path or "/") + ("?" + u.query if u.query else "")
        hits = [(n, a) for n, a, p in self.rules if p.match(path)]
        if not hits:
            return True
        return max(hits, key=lambda x: (x[0], x[1]))[1]


def load_robots(url, host):
    """-> Robots 또는 None(제한 없음). RFC 9309: 2xx 면 규칙을 읽고, 4xx·리다이렉트 반복·연결 실패는 제한 없음, 5xx 는 전부 금지."""
    import urllib.error
    import urllib.request
    try:
        req = urllib.request.Request(f"{urlparse(url).scheme}://{host}/robots.txt", headers={"User-Agent": "Mozilla/5.0"})
        body = urllib.request.urlopen(req, timeout=10).read(500_000).decode("utf-8", "replace")
        return Robots(body)
    except urllib.error.HTTPError as e:
        return Robots("User-agent: *\nDisallow: /") if 500 <= e.code < 600 else None
    except Exception:
        return None


def same_site(h, host):
    strip = lambda x: (x or "").lower().removeprefix("www.")
    return strip(h) == strip(host)


def frame_prefix(fr):
    """10-19(7-37절): 요강대로 맨 바깥 문서부터 iframe 마다 `iframe[src="..."] >>> ` 를 잇는다(전에는 가장 안쪽 하나만 적었다).
    src 는 페이지에 적힌 속성값을 그대로 쓰고, 못 읽으면 프레임 주소를 쓴다."""
    # 10-21(진행보고서 7-83절): 요강 붙임4 「src가 상대 경로인 경우 절대 주소로 바꿔 기재」 -> 바깥 문서 주소 기준으로 절대 주소로 바꾼다
    from urllib.parse import urljoin
    chain = []
    f = fr
    while f is not None and f.parent_frame is not None:
        try:
            src = f.frame_element().get_attribute("src") or f.url
        except Exception:
            src = f.url
        try:
            src = urljoin(f.parent_frame.url, src.strip())
        except Exception:
            pass
        src = src.replace('"', "%22")
        chain.append(f'iframe[src="{src}"] >>> ')
        f = f.parent_frame
    return "".join(reversed(chain))


FRAME_JS = """(e) => { const r = e.getBoundingClientRect(); const sx = window.scrollX, sy = window.scrollY;
  const off = (r.right + sx <= 0) || (r.bottom + sy <= 0) || (r.left + sx >= Math.max(document.documentElement.scrollWidth, window.innerWidth) + 500) ? 1 : 0;
  let op = 1; for (let a = e; a; a = a.parentElement) { const v = parseFloat(getComputedStyle(a).opacity); if (!isNaN(v)) op *= v; }
  return [off, op]; }"""


def frame_hidden(fr):
    """10-19(7-37절): iframe 요소 자체가 바깥 문서에서 화면 밖이거나 투명하면(겹친 iframe 은 바깥까지 누적) 그 안 요소에 표지를 단다.
    -> {"frOff": 1} / {"frOp": 누적 불투명도}. 규칙(rules4)이 이 표지를 OFFSCREEN·TRANSPARENT 근거로 쓴다."""
    off, op = 0, 1.0
    f = fr
    while f is not None and f.parent_frame is not None:
        try:
            o, a = f.frame_element().evaluate(FRAME_JS)
            off, op = max(off, o), op * a
        except Exception:
            pass
        f = f.parent_frame
    return {"frOff": off, "frOp": op}


LATE_MS = 1200  # networkidle 은 통신이 0.5초 멎으면 끝나 setTimeout 삽입보다 먼저 끝날 수 있다


WORKERS = 4  # 10-20(7-56절): 동시에 여는 브라우저 수


def fetch(pg, u):
    """한 쪽을 열어 후보·링크·추가 유형 후보를 모은다(브라우저 일만, 판정 없음). 작업 스레드에서 돈다."""
    try:
        resp = pg.goto(u, wait_until="load", timeout=20000)
        try:  # 불러온 뒤 자바스크립트로 다른 주소로 넘어가는 첫 화면이 있어, 잠잠해질 때까지 조금 기다린다
            pg.wait_for_load_state("networkidle", timeout=2500)
        except Exception:
            pass
        pg.wait_for_timeout(LATE_MS)  # 10-19(7-36절): 불러온 뒤 타이머로 늦게 끼워 넣는 요소(예: 650ms 뒤 광고 <p>)를 기다린다
    except Exception as e:
        return {"url": u, "error": str(e)[:120]}
    fu = norm(pg.url)  # 결과에는 실제로 도착한 페이지 주소를 쓴다(요강: 검출 항목이 있는 페이지의 전체 URL)
    rows, links, eitems = [], [], []
    frames = [(pg.main_frame, "")] + [(fr, frame_prefix(fr)) for fr in pg.frames[1:] if fr.url and fr.url.startswith("http")]
    for fr, prefix in frames:
        try:
            res = fr.evaluate(PAGE_JS, [MAX_CAND, []])
        except Exception:
            continue
        if not prefix:
            links = res["links"]
        fh_ = frame_hidden(fr) if prefix else {}
        eitems += extra_mod.collect(fr, prefix)
        if not prefix:
            try:
                eitems += extra_mod.collect_entities(fr, resp.text() if resp else "")
            except Exception:
                pass
        for c in res["cands"]:
            rows.append({"sid": fu + "|" + prefix, "cat": "", "i": c["i"], "parent": c["parent"], "tag": c["tag"],
                         "text": c["text"], "href": c.get("href", ""), "f": dict(c["f"], **fh_), "lab": {t: 0 for t in MAIN4},
                         "t_skip": 0, "sel": prefix + c["sel"], "url": fu})
    try:  # 10-21 v2r(진행보고서 7-80절): 쪽 제목을 AI 재질문 맥락으로 쓴다
        title = pg.title()[:120]
    except Exception:
        title = ""
    for r in rows:
        r["ptitle"] = title
    return {"url": u, "final": fu, "host": urlparse(pg.url).hostname, "rows": rows, "links": links, "eitems": eitems}


def scan(url, run, out, max_pages, minutes, delay, report="block", dump=False, judge=None, extra=(), entry_url=None, started_at=None):
    """extra: 같은 크롤로 다른 보고 방식 결과도 result_<방식>.json 으로 낸다(10-20, 7-47절. 크롤 차이 없이 방식만 비교).
    judge: llm_judge.Judge 이면 애매한 후보만 언어 모델에 2차 판정을 묻는다(10-19 API 판, 진행보고서 7-30절). None 이면 이전과 똑같다."""
    model = pickle.load(open(Path(run) / "model.pkl", "rb"))
    rules4.OPTS["hg2"] = bool(getattr(model, "hg2", False))  # 10-20 HG 보강(진행보고서 7-57절), 모델 표지로 켠다
    rules4.OPTS["jl_both"] = bool(getattr(model, "jl_both", False))  # 10-21 자모+영문 낱말에 HG·JAMO 둘 다(7-66절)
    rules4.OPTS["numform"] = bool(getattr(model, "numform", False))  # 10-21 번호 기호만 있는 HG 는 뺀다(7-78절)
    rules4.OPTS["jl_both"] = bool(getattr(model, "jl_both", False))
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    kst = timezone(timedelta(hours=9))
    # 10-21(7-83절): 요강 meta.started_at 「탐지 시작(URL 입력/탐지) 시각」, entry_url 「입력값으로 전달받은 진입 URL」
    t0 = started_at if started_at is not None else time.time()
    started = datetime.fromtimestamp(t0, kst)
    entry = url if entry_url is None else entry_url
    host = urlparse(url).hostname
    # 10-17: urllib.robotparser 대신 RFC 9309 판정(Robots). robotparser 는 robots.txt 를 못 읽으면(리다이렉트 반복 등)
    # 모든 주소를 금지로 답해 법무부 0쪽, 가장 긴 규칙 우선을 안 따라 국방부 0쪽이었다.
    rp = load_robots(url, host)
    seen, q, found, pages = {norm(url)}, deque([url]), [], []
    found_x = {m: [] for m in extra}
    found_e = []  # 추가 유형(ETC) 검출
    def process(fx):
        """브라우저에서 모은 한 쪽(fx)을 판정하고 링크를 큐에 넣는다. 메인 스레드에서만 돈다."""
        nonlocal host
        if fx.get("error"):
            pages.append({"url": fx["url"], "error": fx["error"]})
            return
        u, rows, links, eitems = fx["final"], fx["rows"], fx["links"], fx["eitems"]
        seen.add(u)
        if not pages:  # 첫 페이지가 다른 호스트로 넘어가면(예: www 없는 주소) 그 호스트를 기준으로 삼는다
            host = fx["host"] or host
        if dump and rows:  # 후보를 저장해 두면 다시 크롤링하지 않고 판정기만 바꿔 볼 수 있다(eval_sites.py)
            with open(out / "rows.jsonl", "a", encoding="utf-8") as fh:
                for r in rows:
                    fh.write(json.dumps({k: r[k] for k in ("sid", "i", "parent", "tag", "text", "href", "f", "sel", "url")}, ensure_ascii=False) + "\n")
        if rows:
            rule_cache(rows)
            if getattr(model, "ui", False):
                ui_skip(rows)
            if getattr(model, "stack", False):  # 10-20 v9 규칙 S(진행보고서 7-44절)
                rules4.stack_skip(rows)
            if getattr(model, "garble", False):  # 10-20 깨진 글자 거르기(진행보고서 7-60절)
                rules4.garble_skip(rows)
            key = {(r["sid"], r["i"]): r for r in rows}
            ad = model.ad.score(rows)
            if getattr(model, "conj_strong", False):  # 10-21 조합형 자모는 강한 증거(7-69절)
                ad = rules4.conj_boost(rows, ad, getattr(model, "conj_floor", 0.99))  # 10-21 C안: 문턱 살짝 위로만(7-70절)
            if judge is not None:
                ad = judge.adjust(rows, ad, model.thr)
            det = model.detect(rows, ad)
            if getattr(model, "emit_all", False):  # 10-21 걸린 기법 모두 내기(7-81절)
                det = rules4.emit_all(rows, det)
            try:  # 10-20(7-58절): 글자 변형 추가 유형(광고 점수 0.5 이상 잎 요소)
                for t, sel, ev, pr, why in extra_mod.judge_rows(rows, ad):
                    found_e.append({"url": u, "is_violation": True, "location": sel, "evidence_text": ev, "technique": "ETC",
                                    "extra_finding": t, "_ad": round(pr, 3), "_why": why})
            except Exception as e:
                pages.append({"url": u, "extra_error": str(e)[:120]})
            for m_, dst in [(report, found)] + list(found_x.items()):
                for (sid, i, t), (pr, why) in sorted(relocate(rows, det, m_).items()):
                    r = key[(sid, i)]
                    dst.append({"url": r["url"], "is_violation": True, "location": r["sel"], "evidence_text": r["text"][:5000],
                                "technique": t, "_ad": round(pr, 3), "_why": why, "_llm": r.get("_llm")})
        try:
            for t, sel, ev, pr, why in extra_mod.judge(eitems, model, u, judge if getattr(judge, "wide", False) else None):
                found_e.append({"url": u, "is_violation": True, "location": sel, "evidence_text": str(ev)[:5000], "technique": "ETC",
                                "extra_finding": t, "_ad": round(pr, 3), "_why": why})
        except Exception as e:  # 추가 유형이 실패해도 4종 검사는 그대로 간다
            pages.append({"url": u, "extra_error": str(e)[:120]})
        # 10-19(7-35절): 같은 문서를 두 주소(쿼리만 다름 등)로 연 것을 가리려고 후보 요소(선택자·글자)로 지문을 남긴다
        sig = hashlib.sha1(json.dumps(sorted((r["sel"], r["text"]) for r in rows), ensure_ascii=False).encode("utf-8")).hexdigest() if rows else None
        pages.append({"url": u, "cands": len(rows), "sig": sig})
        for l in links:
            l = norm(l)
            pu = urlparse(l)
            if same_site(pu.hostname, host) and pu.scheme in ("http", "https") and l not in seen and not l.lower().endswith(SKIP_EXT):
                seen.add(l)
                q.append(l)

    # 10-20(진행보고서 7-56절): 검출 시간(20점)을 줄이려고 브라우저 일(열기·후보 뽑기)을 WORKERS 개 스레드가 나눠 한다.
    # 스레드마다 자기 Playwright·브라우저를 쓴다(Playwright 동기 객체는 만든 스레드에서만 쓸 수 있음). 판정·큐 관리는 메인 스레드.
    tasks, results = queue.Queue(), queue.Queue()

    def worker():
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(channel="msedge", headless=True)
            pg = b.new_context(viewport={"width": 1280, "height": 800}).new_page()
            while True:
                u = tasks.get()
                if u is None:
                    break
                try:
                    results.put(fetch(pg, u))
                except Exception as e:  # 페이지가 망가지면 새 페이지로 바꾸고 이 쪽은 오류로 남긴다
                    results.put({"url": u, "error": str(e)[:120]})
                    try:
                        pg.close()
                    except Exception:
                        pass
                    pg = b.new_context(viewport={"width": 1280, "height": 800}).new_page()
                time.sleep(delay)
            b.close()

    nw = max(1, int(os.environ.get("ADDETECTOR_WORKERS", WORKERS)))
    ths = [threading.Thread(target=worker, daemon=True) for _ in range(nw)]
    for th in ths:
        th.start()
    inflight = 0
    while True:
        while q and inflight < (1 if not pages else nw) and len(pages) + inflight < max_pages and time.time() - t0 < minutes * 60:
            u = q.popleft()
            if rp is not None and not rp.can_fetch(u):
                continue
            tasks.put(u)
            inflight += 1
        if inflight == 0:
            break
        try:
            fx = results.get(timeout=1.0)
        except queue.Empty:
            if time.time() - t0 > minutes * 60 + 30:  # 상한 뒤 30초가 지나도 안 끝난 쪽은 버린다
                break
            if not any(th.is_alive() for th in ths):  # 10-21(7-83절): 브라우저를 못 띄워 작업 스레드가 모두 끝났으면 바로 멈춘다
                pages.append({"url": url, "error": "브라우저 작업 스레드가 모두 멈춤"})
                break
            continue
        inflight -= 1
        process(fx)
    for _ in ths:
        tasks.put(None)
    for th in ths:
        th.join(timeout=20)
    # 10-19(7-35절): 내용이 똑같은 쪽이 여러 주소로 열렸으면 한 주소(쿼리 없는 것, 다음은 짧은 것)의 검출만 남긴다.
    # 내용이 다른 쪽(예: ?page=1 과 ?page=2)은 지문이 달라 그대로다. 공통 영역 광고가 여러 쪽에 있는 경우도 쪽마다 남는다.
    groups = {}
    for pg_ in pages:
        if pg_.get("sig"):
            groups.setdefault(pg_["sig"], []).append(pg_["url"])
    drop = set()
    for us in groups.values():
        if len(set(us)) > 1:
            keep = min(set(us), key=lambda x: (bool(urlparse(x).query), len(x), x))
            drop |= set(us) - {keep}
    done = datetime.now(kst)

    def finish(fs, mode):
        fs = [f for f in fs if f["url"] not in drop]
        uniq, outf = set(), []
        for f in fs:
            k = (f["url"], f["location"], f["technique"])
            if k not in uniq:
                uniq.add(k)
                outf.append(dict(f, id=f"f_{len(outf) + 1:03d}"))
        res = {"meta": {"topic": "TOPIC", "entry_url": entry, "started_at": started.isoformat(timespec="seconds"),
                        "finished_at": done.isoformat(timespec="seconds"), "elapsed_sec": round(time.time() - t0, 1),
                        "tool_version": f"{Path(run).name}-{mode}{'+api' if judge is not None else ''}"},
               "findings": [{k: f[k] for k in ("id", "url", "is_violation", "location", "evidence_text", "technique")} for f in outf]}
        return res, outf
    result, outf = finish(found, report)
    (out / "result.json").write_bytes(json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8"))
    ex = [f for f in found_e if f["url"] not in drop]
    uq, exf = set(), []
    for f in ex:
        k = (f["url"], f["location"], f["extra_finding"])
        if k not in uq:
            uq.add(k)
            exf.append(dict(f, id=f"e_{len(exf) + 1:03d}"))
    result_extra = {"meta": dict(result["meta"]),
                    "findings": [{k: f[k] for k in ("id", "url", "is_violation", "location", "evidence_text", "technique", "extra_finding")} for f in exf]}
    (out / "result_extra.json").write_bytes(json.dumps(result_extra, ensure_ascii=False, indent=2).encode("utf-8"))
    for m_, fs in found_x.items():
        (out / f"result_{m_}.json").write_bytes(json.dumps(finish(fs, m_)[0], ensure_ascii=False, indent=2).encode("utf-8"))
    dbg = {"pages": pages, "findings": outf, "extra_findings": exf, "same_doc_dropped": sorted(drop)}
    if judge is not None:
        dbg["api"] = judge.summary()
    (out / "debug.json").write_text(json.dumps(dbg, ensure_ascii=False, indent=2), encoding="utf-8")
    return result, pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-pages", type=int, default=60)
    ap.add_argument("--minutes", type=float, default=10)
    ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--report", choices=MODES, default="block")  # 10-19 hedge -> inner(7-37절), 10-20 사용자 결정 block(7-50절)
    ap.add_argument("--dump", action="store_true", help="후보를 out/rows.jsonl 로 저장")
    ap.add_argument("--extra", nargs="*", choices=MODES, default=[], help="같은 크롤로 이 보고 방식 결과도 result_<방식>.json 으로(7-47절)")
    ap.add_argument("--api", action="store_true", help="애매한 후보만 언어 모델에 2차 판정(키: ANTHROPIC_API_KEY 또는 api_key.txt)")
    a = ap.parse_args()
    judge = None
    if a.api:
        from llm_judge import Judge, Judge2
        judge = Judge2() if os.environ.get("ADDETECTOR_API_MODE") == "v2" else Judge()  # 10-21 v2(진행보고서 7-65절)
    res, pages = scan(a.url, a.run, a.out, a.max_pages, a.minutes, a.delay, a.report, a.dump, judge, a.extra)
    if judge is not None:
        print("API:", judge.summary())
    print(f"페이지 {len(pages)}쪽, 검출 {len(res['findings'])}건, {res['meta']['elapsed_sec']}초 -> {a.out}/result.json")


if __name__ == "__main__":
    main()
