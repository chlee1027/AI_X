"""불법광고 탐지 도구 (trial). 진입 URL 하나 -> 크롤링 -> 렌더링 -> 탐지 -> result.json · result_extra.json

  python run.py <진입 URL> [--out 폴더] [--max-pages N] [--budget 초] [--workers N]

- 브라우저: Edge(channel="msedge") 1순위, 없으면 Playwright Chromium.
- 범위: 진입 URL 과 같은 호스트·포트. 요강 URL 비교 규칙대로 합친다(# 이하·끝 / 무시, 쿼리는 항목 순서만 다르면 같은 페이지).
- iframe: 페이지 안의 모든 프레임(여러 겹)을 검사해 location 을 iframe[src="절대주소"] >>> 선택자 로 쓴다.
  iframe 주소는 따로 크롤링하지 않는다(같은 광고를 다른 url 로 두 번 내지 않게).
- 시간: 예산(기본 25분)을 넘으면 새 페이지를 열지 않고 그때까지의 결과를 쓴다. 어떤 예외에도 결과 파일은 남긴다.
- 결과 파일은 이 파일이 있는 폴더(또는 --out)에 UTF-8(BOM 없음)으로 쓴다.
"""
import argparse
import os
import asyncio
import json
from collections import defaultdict
import pickle
import re
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urljoin, urlsplit, urlunsplit

HERE = Path(__file__).resolve().parent
# 탐지 엔진: 저장소에서는 B_detector/, 시험판에서는 dev/. exe 로 묶으면 모델과 모듈이 실행 파일 옆(_MEIPASS)에 들어간다
DET = HERE if getattr(sys, "frozen", False) else (HERE.parent / "B_detector" if (HERE.parent / "B_detector").exists() else HERE.parent / "dev")
MODELS = DET / "models" if (DET / "models").exists() else HERE / "models"
sys.path.insert(0, str(DET))

from detector import Detector  # noqa: E402
from extra import Extra  # noqa: E402
from llm import LLMGate  # noqa: E402

KST = timezone(timedelta(hours=9))
PROBE = (HERE / "page_probe.js").read_text(encoding="utf-8")
SKIP_EXT = re.compile(r"\.(jpg|jpeg|png|gif|webp|svg|ico|pdf|zip|hwp|hwpx|docx?|xlsx?|pptx?|mp4|mp3|avi|css|js|xml|json|txt)$", re.I)
VERSION = "trial-0.2"


def norm_url(u):
    s = urlsplit(u)
    q = sorted(parse_qsl(s.query, keep_blank_values=True))
    path = s.path.rstrip("/") or "/"
    return urlunsplit(("", s.netloc.lower(), path, urlencode(q), ""))


def same_site(u, entry):
    a, b = urlsplit(u), urlsplit(entry)
    ha = (a.hostname or "").removeprefix("www.")
    hb = (b.hostname or "").removeprefix("www.")
    return a.scheme in ("http", "https") and ha == hb and (a.port or 0) == (b.port or 0)


URL_RE = re.compile(r"(?:https?:)?//\S+|url\([^)]*\)", re.I)
TEMPLATE_MIN = 5       # 같은 위치·기법·글자가 이 수 이상의 페이지에서 나오고
TEMPLATE_SHARE = 0.3   # 방문 페이지의 이 비율 이상이면 사이트 공통 틀(머리말·메뉴·꼬리말)로 본다
TEMPLATE_KEEP = 0.9    # 공통 틀 출력은 글자만의 내용 점수가 이 이상일 때만 남긴다


def template_filter(findings, n_pages, content):
    """사이트 공통 틀의 출력 거르기(실제 누리집 3차: 메뉴 링크 하나가 모든 페이지에서 반복돼 오탐 94건).
    요강 채점이 (url, 위치, 기법) 단위라 공통 틀의 오탐 하나는 페이지 수만큼 곱해진다. 반대로 사이트 전체에 심은 진짜 광고도
    같은 모양으로 반복되므로 버리지 않고 더 높은 문턱으로 다시 판정한다. 반환: (남긴 출력, 거른 건수)."""
    groups = defaultdict(list)
    for f in findings:
        groups[(f["location"], f["technique"] + "/" + f.get("extra_finding", ""), f["evidence_text"].strip())].append(f)
    need = max(TEMPLATE_MIN, TEMPLATE_SHARE * n_pages)
    tmpl = [k for k, v in groups.items() if len({norm_url(f["url"]) for f in v}) >= need]
    if not tmpl:
        return findings, 0
    # 다시 판정할 때는 주소를 지운 글자만 본다(주소만 붙어도 점수가 오르는 편향, 10절). 글자가 남지 않으면 거른다
    txt = [URL_RE.sub(" ", k[2]).strip() for k in tmpl]
    keep = {k for k, t, p in zip(tmpl, txt, content.proba([t or "-" for t in txt])) if t and p >= TEMPLATE_KEEP}
    drop = {id(f) for k in tmpl if k not in keep for f in groups[k]}
    return [f for f in findings if id(f) not in drop], len(drop)


class Tool:
    def __init__(self, entry, out, max_pages, budget, workers, block_external=False):
        self.block_external = block_external
        self.entry = entry
        self.out = Path(out)
        self.max_pages = max_pages
        self.budget = budget
        self.workers = workers
        m = pickle.load((MODELS / "models.pkl").open("rb"))
        cfg = json.load((MODELS / "config.json").open(encoding="utf-8"))
        th = cfg["main"]
        # 설정 파일의 규칙 값(hide·text·hide_ext·fallback·ext_own·need_letter·menu_hosts)을 통째로 넘긴다
        self.det = Detector(m["content"], dict(th), th["mode"], th["jamo_guard"], th.get("dedupe", True))
        self.ext = Extra(m["content"], cfg["extra"], m["link"])
        # 3단: 키가 있을 때만 경계 점수(0.35 ~ 문턱) 후보를 모아 끝에서 LLM 에 묻는다
        self.llm = LLMGate(HERE)
        self.det_low = Detector(m["content"], dict(th) | {"hide": 0.35, "text": 0.35, "hide_ext": min(0.35, th["hide_ext"])},
                                th["mode"], th["jamo_guard"], th.get("dedupe", True)) if self.llm.client else None
        self.pending = []
        self.site = (urlsplit(entry).hostname or "").removeprefix("www.")
        self.findings, self.extra = [], []
        self.seen_f = set()
        self.visited = []
        self.landed = set()  # 넘겨져 도착한 주소(같은 곳에 여러 번 도착해도 한 번만 검사)
        self.errors = []
        self.skipped = 0
        self.retried = 0
        self.t0 = time.time()
        self.started = datetime.now(KST)

    def trace(self, msg):
        with (self.out / "trace.log").open("a", encoding="utf-8") as f:
            f.write(f"{time.time() - self.t0:8.2f} {msg}\n")

    def over(self):
        return time.time() - self.t0 > self.budget

    async def frame_prefix(self, fr):
        chain = []
        while fr.parent_frame is not None:
            el = await fr.frame_element()
            src = await el.get_attribute("src") or ""
            chain.insert(0, f'iframe[src="{urljoin(fr.parent_frame.url, src)}"]')
            fr = fr.parent_frame
        return "".join(c + " >>> " for c in chain)

    def add(self, store, url, loc, ev, tech, extra=None):
        key = (norm_url(url), loc, tech, extra)
        if key in self.seen_f:
            return
        self.seen_f.add(key)
        f = {"id": "", "url": url, "is_violation": True, "location": loc, "evidence_text": ev[:500], "technique": tech}
        if extra:
            f["extra_finding"] = extra
        store.append(f)

    async def scan_frame(self, fr, page_url):
        els = await fr.evaluate(PROBE)
        doc = {"els": els}
        main = self.det.detect(doc, self.site)
        ext = self.ext.detect(doc, self.site)
        low = sorted(set(self.det_low.detect(doc, self.site)) - set(main)) if self.det_low else []
        want = sorted({i for i, _ in main} | {i for i, _ in ext} | {i for i, _ in low})
        # 실측 진단용: 출력이 난 페이지의 요소 특징을 남겨 두면 규칙을 고친 뒤 크롤링 없이 다시 대 볼 수 있다
        if want and os.environ.get("TOOL_SAVE_FEAT"):
            with (self.out / "page_features.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps({"url": page_url, "site": self.site, "els": els}, ensure_ascii=False) + "\n")
        if not want:
            return
        sels = await fr.evaluate("(ids) => ids.map(i => window.__probeSel(i))", want)
        sel = dict(zip(want, sels))
        pre = await self.frame_prefix(fr)
        by = {e["i"]: e for e in els}
        for i, tech in main:
            e = by[i]
            self.add(self.findings, page_url, pre + sel[i], (e["own"].strip() or e["text"].strip()), tech)
        for i, tech in low:
            e = by[i]
            self.pending.append((page_url, pre + sel[i], (e["own"].strip() or e["text"].strip()), tech))
        for i, t in ext:
            e = by[i]
            ev = e.get("attr_content") or (e["href"] if t in ("LINK_CLOAKING", "ENCODING") else "") or e.get("pseudo") \
                if t in ("META_CLOAKING", "LINK_CLOAKING", "ENCODING", "CSS_CONTENT") else (e["own"].strip() or e["text"].strip())
            self.add(self.extra, page_url, pre + sel[i], ev or e["text"].strip(), "ETC", t)

    async def visit(self, page, url, queue, seen):
        """한 페이지를 열어 검사하고 링크를 큐에 넣는다. 다른 곳으로 이동해 끊기면 RuntimeError("moved")."""
        resp = await page.goto(url, wait_until="load", timeout=15000)
        ctype = (resp.headers.get("content-type", "") if resp else "")
        if resp is None or resp.status >= 400 or "html" not in ctype:
            self.skipped += 1
            return
        await page.wait_for_timeout(150)
        if not self.visited:
            await page.wait_for_timeout(1000)  # 첫 화면은 안내 화면이 잠시 뒤 본 화면으로 넘기는 경우가 있다
        # 열린 뒤 스크립트가 늦게 다른 주소로 보내면(실제 누리집 경찰청) 검사 도중 문서가 사라진다. 그때는 도착을 기다려 한 번 더 본다
        for attempt in range(2):
            url, nav = await self.land_and_scan(page, url, seen)
            if url is None:
                return
            if not nav:
                break
            self.trace(f"navigated during scan {url} -> {page.url}")
            try:
                await page.wait_for_load_state("load", timeout=10000)
            except Exception:
                pass
            await page.wait_for_timeout(300)
        added = await self.collect_links(page, queue, seen)
        if added == 0 and len(self.visited) <= 1:
            # 첫 화면에 같은 사이트 링크가 하나도 없으면 안내 화면일 수 있다. 3초 안에 넘어가면 도착한 곳을 검사한다
            try:
                await page.wait_for_url(lambda u: norm_url(u.split("#")[0]) != norm_url(url), timeout=3000)
                await page.wait_for_load_state("load", timeout=10000)
            except Exception:
                return
            self.trace(f"late move {url} -> {page.url}")
            url, _ = await self.land_and_scan(page, url, seen)
            if url is not None:
                await self.collect_links(page, queue, seen)

    async def collect_links(self, page, queue, seen):
        links = await asyncio.wait_for(page.evaluate("() => [...document.querySelectorAll('a[href]')].map(a => a.href)"), timeout=10)
        added = 0
        for h in links:
            h = h.split("#")[0]
            if not h or not same_site(h, self.entry) or SKIP_EXT.search(urlsplit(h).path):
                continue
            k = norm_url(h)
            if k not in seen:
                seen.add(k)
                queue.put_nowait(h)
                added += 1
        return added

    async def land_and_scan(self, page, url, seen):
        """지금 창이 머문 주소를 정해 검사한다. (검사한 주소 또는 None, 검사 중 문서가 넘어갔는가)"""
        if norm_url(page.url) != norm_url(url):
            # 실제 누리집은 첫 화면이 /main.do 같은 곳으로 넘기는 경우가 많다. 같은 사이트 안이면 도착한 주소를 그 페이지로 본다
            try:
                await page.wait_for_load_state("load", timeout=10000)
            except Exception:
                pass
            if not same_site(page.url, self.entry):
                if not self.visited and norm_url(url) == norm_url(self.entry):
                    # 진입 페이지가 다른 호스트로 넘기면(실제 누리집 통계청·환경부) 도착한 호스트를 검사 대상으로 삼는다
                    self.trace(f"entry moved {url} -> {page.url}")
                    self.entry = page.url.split("#")[0]
                    self.site = (urlsplit(self.entry).hostname or "").removeprefix("www.")
                else:
                    raise RuntimeError("moved")
            k = norm_url(page.url.split("#")[0])
            if k in self.landed:
                return None, False
            self.landed.add(k)
            seen.add(k)
            url = page.url.split("#")[0]
        self.visited.append(url)
        for fr in page.frames:
            try:
                await asyncio.wait_for(self.scan_frame(fr, url), timeout=20)
            except Exception as e:  # 프레임 하나가 실패하거나 20초를 넘어도 페이지는 계속
                if fr is page.main_frame and ("context was destroyed" in str(e) or "navigation" in str(e)):
                    self.visited.pop()
                    return url, True
                self.errors.append(f"frame {fr.url[:120]}: {type(e).__name__} {str(e)[:120]}")
        if norm_url(page.url.split("#")[0]) != norm_url(url):  # 검사는 끝났지만 그 사이 넘어감
            return url, True
        return url, False

    async def new_page(self, ctx):
        page = await ctx.new_page()
        page.on("dialog", lambda d: asyncio.ensure_future(d.dismiss()))  # 조각 속 alert·confirm 이 평가를 막지 않게
        return page

    async def worker(self, ctx, ctx_nojs, queue, seen, active):
        page = await self.new_page(ctx)
        while True:
            if self.over() or len(self.visited) >= self.max_pages:
                break
            try:
                url = queue.get_nowait()
            except asyncio.QueueEmpty:
                if active[0] == 0:
                    break
                await asyncio.sleep(0.05)
                continue
            active[0] += 1
            self.trace(f"start {url[:100]}")
            try:
                await self.visit(page, url, queue, seen)
            except Exception as e:
                msg = str(e)
                if "moved" in msg or "interrupted by another navigation" in msg:
                    # 페이지 스크립트가 다른 곳으로 보냄(메타 새로고침·자바스크립트 이동) -> 스크립트를 끈 창에서 한 번 더
                    self.retried += 1
                    p2 = await self.new_page(ctx_nojs)
                    try:
                        await self.visit(p2, url, queue, seen)
                    except Exception as e2:
                        self.errors.append(f"{url}: retry {type(e2).__name__} {str(e2).splitlines()[0][:150] if str(e2) else ''}")
                    finally:
                        try:
                            await asyncio.wait_for(p2.close(), timeout=5)
                        except Exception:
                            pass
                elif "ERR_HTTP_RESPONSE_CODE_FAILURE" in msg:
                    self.skipped += 1
                else:
                    self.errors.append(f"{url}: {type(e).__name__} {msg.splitlines()[0][:200] if msg else ''}")
                    try:
                        await asyncio.wait_for(page.close(), timeout=5)
                    except Exception:
                        pass
                    page = await self.new_page(ctx)
            finally:
                active[0] -= 1
                self.trace(f"end {url[:100]}")
        self.trace("worker exit")
        try:
            await asyncio.wait_for(page.close(), timeout=5)  # 조각 스크립트가 남긴 상태로 close 가 안 돌아오는 경우가 있었다
        except Exception as e:
            self.errors.append(f"page close: {type(e).__name__}")
        self.trace("page closed")

    async def crawl(self):
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            try:
                browser = await p.chromium.launch(channel="msedge")
            except Exception as e_edge:
                try:
                    browser = await p.chromium.launch()
                except Exception:
                    # 둘 다 없으면 원인을 알 수 있게 남긴다(결과 파일은 main 의 finally 에서 그대로 쓴다)
                    raise RuntimeError("브라우저를 열 수 없다: Microsoft Edge 가 필요하다"
                                       "(또는 'python -m playwright install chromium')") from e_edge
            ctx = await browser.new_context(viewport={"width": 1280, "height": 900}, ignore_https_errors=True)
            ctx_nojs = await browser.new_context(viewport={"width": 1280, "height": 900}, ignore_https_errors=True,
                                                 java_script_enabled=False)
            if self.block_external:
                # 시험용: 진입 호스트 밖 요청(조각에 남은 스팸 사이트 스크립트·이미지)을 막는다
                async def guard(route):
                    u = route.request.url
                    if u.startswith("http") and not same_site(u, self.entry):
                        await route.abort()
                    else:
                        await route.continue_()
                await ctx.route("**/*", guard)
                await ctx_nojs.route("**/*", guard)
            queue = asyncio.Queue()
            seen = {norm_url(self.entry)}
            queue.put_nowait(self.entry)
            active = [0]
            await asyncio.gather(*(self.worker(ctx, ctx_nojs, queue, seen, active) for _ in range(self.workers)))
            self.trace("all workers done")
            try:
                await asyncio.wait_for(browser.close(), timeout=10)
            except Exception as e:
                self.errors.append(f"browser close: {type(e).__name__}")
            self.trace("browser closed")

    def write(self):
        if self.pending and self.llm.client:
            verdict = self.llm.classify([p[2] for p in self.pending])
            for (u, loc, ev, tech), v in zip(self.pending, verdict):
                if v:
                    self.add(self.findings, u, loc, ev, tech)
        self.findings, self.template_dropped = template_filter(self.findings, len(self.visited), self.det.c)
        self.extra, self.template_dropped_extra = template_filter(self.extra, len(self.visited), self.det.c)
        fin = datetime.now(KST)
        meta = {"topic": "TOPIC", "entry_url": self.entry, "started_at": self.started.isoformat(timespec="seconds"),
                "finished_at": fin.isoformat(timespec="seconds"), "elapsed_sec": round(time.time() - self.t0, 2),
                "tool_version": VERSION}
        for k, f in enumerate(self.findings, 1):
            f["id"] = f"f_{k:05d}"
        for k, f in enumerate(self.extra, 1):
            f["id"] = f"x_{k:05d}"
        self.out.mkdir(parents=True, exist_ok=True)
        (self.out / "result.json").write_text(json.dumps({"meta": meta, "findings": self.findings}, ensure_ascii=False, indent=1), encoding="utf-8")
        (self.out / "result_extra.json").write_text(json.dumps({"meta": meta, "findings": self.extra}, ensure_ascii=False, indent=1), encoding="utf-8")
        log = {"pages": len(self.visited), "skipped_non_html_or_4xx": self.skipped, "retried_without_js": self.retried, "errors": self.errors[:200], "n_errors": len(self.errors),
               "findings": len(self.findings), "extra": len(self.extra), "llm": self.llm.report(), "llm_pending": len(self.pending),
               "template_dropped": self.template_dropped,
               "template_dropped_extra": self.template_dropped_extra, "elapsed_sec": meta["elapsed_sec"]}
        (self.out / "run_log.json").write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps(log | {"errors": self.errors[:5]}, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("entry")
    ap.add_argument("--out", default=str(HERE))
    ap.add_argument("--max-pages", type=int, default=5000)
    ap.add_argument("--budget", type=float, default=25 * 60)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--block-external", action="store_true", help="진입 호스트 밖 요청 차단(시험용)")
    a = ap.parse_args()
    if os.environ.get("TOOL_DUMP_AFTER"):
        import faulthandler
        faulthandler.dump_traceback_later(float(os.environ["TOOL_DUMP_AFTER"]), repeat=False,
                                          file=open(Path(a.out) / "stack_dump.txt", "w"))
    tool = Tool(a.entry, a.out, a.max_pages, a.budget, a.workers, a.block_external)
    tool.out.mkdir(parents=True, exist_ok=True)
    (tool.out / "trace.log").write_text("", encoding="utf-8")
    try:
        asyncio.run(tool.crawl())
    except Exception:
        tool.errors.append(traceback.format_exc()[-800:])
    finally:
        tool.write()


if __name__ == "__main__":
    main()
