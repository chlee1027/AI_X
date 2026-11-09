"""이미지 수집기 v1 (2026-11-04, 재계획 6절 채현 몫 「크롤러에 이미지 수집 추가」).

씨앗 페이지(seeds.csv)를 하나씩 Playwright 로 렌더링하고, 페이지에 박힌 이미지(img, input[type=image], CSS 배경)를
받아 데이터 명세 3·5절 형식으로 기록한다.

접속 범위 (명세 3절 「접속 범위」, 재계획 3절 「수집 원칙」):
  - 씨앗 페이지만 연다. 페이지 안의 링크는 기록(link_href)만 하고 따라가지 않는다.
  - 씨앗 주소가 다른 등록 도메인으로 3xx 리디렉트하면 열지 않는다(먼저 리디렉트 없이 한 번 물어본다).
  - 렌더링 중 메인 프레임이 다른 등록 도메인으로 이동하려 하면(JS·meta refresh) 그 이동을 끊는다.
  - 다른 등록 도메인의 iframe 문서도 끊는다(불법 사이트 페이지를 통째로 끼워 넣는 경우가 있어 보수적으로 막음).
  - 팝업 창은 바로 닫고, 다운로드는 받지 않는다.
  - 이미지·CSS·스크립트 같은 하위 자원은 외부 서버에 있어도 받는다(피해 페이지 렌더링에 필요).
  - robots.txt(씨앗 페이지 호스트, 직접 받는 이미지 호스트)를 지키고 페이지 사이에 1초 쉰다.
저장하지 않는 이미지 (명세 3절): 가로나 세로 32px 미만(too_small), 성인 노출 분류기 점수가 문턱 이상(adult).
  둘 다 파일을 버리고 skipped.csv 에 page_url, source_url, reason 만 남긴다. 성인 이미지는 사람이 열어 보지 않도록
  저장 전에 메모리에서 거른다(nsfw.py).

출력 (--out 아래, 샤드마다 접미사 _<i>):
  images/<sha1 앞 16>.<ext>   내용이 같은 파일은 하나만. image_id 접두어(rpos_/rgen_)는 라벨 뒤 export 때 붙인다
  occurrences_<i>.csv          (페이지, 이미지 요소) 한 쌍에 한 줄. meta.csv 의 화면 정보 열 원본
  skipped_<i>.csv              page_url, source_url, reason
  fail_<i>.csv                 받기·풀기 실패(명세 밖 기록. skipped.csv 와 섞지 않는다)
  pages_<i>.csv                페이지 한 장에 한 줄(상태, 제목, 끊은 이동 수, 도박 낱말 수 등)
  pages_text_<i>.jsonl         페이지 보이는 글(같은 페이지의 텍스트 요소와 이미지 요소를 함께 남기기 위함)

사용: python collect.py --seeds seeds.csv --out ../collect [--shard 0 --nshards 3] [--limit N]
"""
import argparse
import csv
import hashlib
import io
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin, urlparse

import tldextract
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nsfw  # noqa: E402
import safe_io  # noqa: E402

KST = timezone(timedelta(hours=9))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/130.0.0.0 Safari/537.36")
MIN_SIDE = 32
MAX_BYTES = 8_000_000
DELAY = 1.0
EXTRACT = tldextract.TLDExtract(suffix_list_urls=())  # 내장 목록만 쓴다(네트워크 없이)

GAMBLE = re.compile(r"slot|gacor|togel|casino|judi|bandar|maxwin|scatter|pragmatic|sbobet|toto|baccarat|poker|betting|"
                    r"카지노|토토|슬롯|바카라|먹튀|홀덤|파워볼|사설|배팅|베팅|꽁머니|가입코드", re.I)


def now():
    return datetime.now(KST).isoformat(timespec="seconds")


def reg_domain(url):
    e = EXTRACT(url)
    return (e.top_domain_under_public_suffix if hasattr(e, "top_domain_under_public_suffix") else e.registered_domain) or urlparse(url).hostname or ""


# ---- robots.txt (1차 scan4.py 의 Robots 와 같은 판정: 가장 긴 규칙이 이기고 길이가 같으면 허용) ----
class Robots:
    def __init__(self, text):
        self.rules, cur_any, in_rules = [], False, False
        for line in text.splitlines():
            line = line.split("#", 1)[0].strip()
            if ":" not in line:
                continue
            k, v = (x.strip() for x in line.split(":", 1))
            k = k.lower()
            if k == "user-agent":
                if in_rules:
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
        u = urlparse(url)
        path = (u.path or "/") + ("?" + u.query if u.query else "")
        hits = [(n, a) for n, a, p in self.rules if p.match(path)]
        return True if not hits else max(hits, key=lambda x: (x[0], x[1]))[1]


_ROBOTS = {}


def robots_ok(url):
    u = urlparse(url)
    key = f"{u.scheme}://{u.netloc}"
    if key not in _ROBOTS:
        try:
            req = urllib.request.Request(key + "/robots.txt", headers={"User-Agent": UA})
            body = urllib.request.urlopen(req, timeout=10).read(500_000).decode("utf-8", "replace")
            _ROBOTS[key] = Robots(body)
        except urllib.error.HTTPError as e:
            _ROBOTS[key] = Robots("User-agent: *\nDisallow: /") if 500 <= e.code < 600 else None
        except Exception:
            _ROBOTS[key] = None
    r = _ROBOTS[key]
    return True if r is None else r.can_fetch(url)


# ---- 페이지 안에서 이미지 요소를 모으는 JS ----
IMG_JS = r"""() => {
  const esc = (s) => (window.CSS && CSS.escape) ? CSS.escape(s) : s;
  const step = (el) => { let s = el.tagName.toLowerCase();
    const cls = Array.from(el.classList).filter(c => /^[A-Za-z_-][\w-]*$/.test(c));
    if (cls.length) s += '.' + cls.map(esc).join('.');
    const p = el.parentElement;
    if (p) { const same = Array.from(p.children).filter(c => c.tagName === el.tagName);
      if (same.length > 1 && !cls.length) s += ':nth-of-type(' + (same.indexOf(el) + 1) + ')';
      else if (same.length > 1) { const sameCls = same.filter(c => c.matches(s)); if (sameCls.length > 1) s += ':nth-of-type(' + (same.indexOf(el) + 1) + ')'; } }
    return s; };
  const sel = (el) => { let parts = [], e = el;
    while (e && e !== document.documentElement) { parts.unshift(step(e));
      const q = parts.join(' > '); try { if (document.querySelectorAll(q).length === 1) return q; } catch (x) {}
      e = e.parentElement; }
    return parts.join(' > '); };
  const shown = (el, r) => { if (r.width <= 0 || r.height <= 0) return false;
    for (let a = el; a; a = a.parentElement) { const c = getComputedStyle(a);
      if (c.display === 'none' || c.visibility === 'hidden' || parseFloat(c.opacity) === 0) return false; }
    return true; };
  const out = []; const sx = window.scrollX, sy = window.scrollY;
  const push = (el, url, kind, nw, nh) => { if (!url || url.startsWith('data:image/gif;base64,R0lGOD')) return;
    const r = el.getBoundingClientRect(); const vis = shown(el, r); const a = el.closest('a[href]');
    out.push({url, element: kind, w: nw || 0, h: nh || 0,
      render_w: vis ? Math.round(r.width) : 0, render_h: vis ? Math.round(r.height) : 0,
      x: Math.round(r.left + sx), y: Math.round(r.top + sy), selector: sel(el),
      link_href: a ? a.href : '', alt: el.getAttribute('alt') || ''}); };
  document.querySelectorAll('img').forEach(el => {
    let u = el.currentSrc || el.src;
    const lazy = el.getAttribute('data-src') || el.getAttribute('data-lazy-src') || el.getAttribute('data-original');
    if ((!u || u.startsWith('data:')) && lazy) u = new URL(lazy, document.baseURI).href;
    push(el, u, 'img', el.naturalWidth, el.naturalHeight); });
  document.querySelectorAll('input[type=image]').forEach(el => push(el, el.src, 'img', 0, 0));
  const all = document.body ? document.body.querySelectorAll('*') : [];
  let n = 0;
  for (const el of all) { if (++n > 8000) break;
    const bg = getComputedStyle(el).backgroundImage;
    if (!bg || bg === 'none') continue;
    for (const m of bg.matchAll(/url\(["']?([^"')]+)["']?\)/g)) push(el, new URL(m[1], document.baseURI).href, 'css_bg', 0, 0); }
  return out;
}"""

OCC_COLS = ["sha1", "file", "source_url", "page_url", "site", "site_type", "element", "w", "h", "render_w", "render_h",
            "x", "y", "selector", "link_href", "alt", "frame", "collected_at"]
PAGE_COLS = ["page_url", "final_url", "site", "site_type", "origin", "status", "title", "n_elems", "n_saved", "n_new",
             "n_small", "n_adult", "n_fail", "blocked_nav", "blocked_iframe", "gamble_hits", "text_len", "crawled_at", "error"]


class Writer:
    def __init__(self, path, cols):
        safe_io.repair_tail(path)
        new = not os.path.exists(path) or os.path.getsize(path) == 0
        self.f = open(path, "a", encoding="utf-8", newline="")
        self.w = csv.DictWriter(self.f, fieldnames=cols, extrasaction="ignore")
        if new:
            self.w.writeheader()

    def row(self, d):
        self.w.writerow(d)
        self.f.flush()


def ext_of(fmt):
    return {"JPEG": "jpg", "PNG": "png", "GIF": "gif", "WEBP": "webp"}.get(fmt)


def decode(data, ctype, url, svg_page):
    """-> (bytes_to_save, ext, PIL 첫 프레임 RGB) 또는 예외. SVG 는 브라우저로 그려 PNG 로 바꾼다(명세 3절)."""
    is_svg = "svg" in (ctype or "") or urlparse(url).path.lower().endswith(".svg") or data[:200].lstrip().startswith((b"<svg", b"<?xml"))
    if is_svg:
        import base64
        b64 = base64.b64encode(data).decode()
        svg_page.set_content(f'<html><body style="margin:0;background:transparent"><img id="i" src="data:image/svg+xml;base64,{b64}"></body></html>')
        svg_page.wait_for_timeout(200)
        box = svg_page.eval_on_selector("#i", "e => [e.naturalWidth, e.naturalHeight]")
        if not box or box[0] < 1 or box[1] < 1:
            raise ValueError("svg_empty")
        w, h = min(box[0], 2000), min(box[1], 2000)
        svg_page.set_viewport_size({"width": max(w, 1), "height": max(h, 1)})
        png = svg_page.locator("#i").screenshot(omit_background=True)
        im = Image.open(io.BytesIO(png))
        return png, "png", im.convert("RGB")
    im = Image.open(io.BytesIO(data))
    ext = ext_of(im.format)
    im.seek(0)
    first = im.convert("RGB")
    if ext is None:  # BMP·ICO 등: PNG 로 바꿔 저장
        buf = io.BytesIO()
        Image.open(io.BytesIO(data)).convert("RGBA").save(buf, "PNG")
        return buf.getvalue(), "png", first
    return data, ext, first


def crawl(args):
    from playwright.sync_api import sync_playwright

    out = os.path.abspath(args.out)
    img_dir = os.path.join(out, "images")
    os.makedirs(img_dir, exist_ok=True)
    sfx = f"_{args.file_shard if args.file_shard is not None else args.shard}"  # 추가 수집은 기존 파일과 안 겹치는 번호로 쓴다
    occ = Writer(os.path.join(out, f"occurrences{sfx}.csv"), OCC_COLS)
    skp = Writer(os.path.join(out, f"skipped{sfx}.csv"), ["page_url", "source_url", "reason"])
    fail = Writer(os.path.join(out, f"fail{sfx}.csv"), ["page_url", "source_url", "reason"])
    pag = Writer(os.path.join(out, f"pages{sfx}.csv"), PAGE_COLS)
    safe_io.repair_tail(os.path.join(out, f"pages_text{sfx}.jsonl"), quoted=False)
    txt = open(os.path.join(out, f"pages_text{sfx}.jsonl"), "a", encoding="utf-8")

    done = set()
    for fn in os.listdir(out):
        if fn.startswith("pages_") and fn.endswith(".csv"):
            done |= {r["page_url"] for r in safe_io.read_csv(os.path.join(out, fn))}
    adult_sha = set()  # 같은 실행 안에서 성인으로 거른 내용은 다시 분류하지 않는다(파일이 없으니 실행 사이에는 다시 분류)

    seeds = list(csv.DictReader(open(args.seeds, encoding="utf-8")))
    seeds = [s for i, s in enumerate(seeds) if i % args.nshards == args.shard and s["page_url"] not in done]
    if args.limit:
        seeds = seeds[: args.limit]
    print(f"shard {args.shard}: {len(seeds)} pages", flush=True)
    if safe_io.paused():
        print("PAUSE: 시작하지 않고 끝낸다", flush=True)
        return

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        svg_ctx = browser.new_context()
        svg_ctx.route("**/*", lambda r: r.abort() if not r.request.url.startswith(("data:", "about:")) else r.continue_())
        svg_page = svg_ctx.new_page()

        for k, s in enumerate(seeds):
            if safe_io.paused():  # 진행 중인 페이지는 이미 마쳤고 기록은 줄마다 flush 됐다
                print(f"PAUSE: {k}/{len(seeds)} 쪽에서 멈춘다", flush=True)
                break
            url, site_type, origin = s["page_url"], s.get("site_type", ""), s.get("origin", "")
            site = reg_domain(url)
            rec = {c: "" for c in PAGE_COLS}
            rec.update(page_url=url, site=site, site_type=site_type, origin=origin, crawled_at=now())
            cnt = dict(n_elems=0, n_saved=0, n_new=0, n_small=0, n_adult=0, n_fail=0, blocked_nav=0, blocked_iframe=0)
            try:
                if not robots_ok(url):
                    rec["status"] = "robots_disallow"
                    pag.row(rec)
                    continue
                ctx = browser.new_context(user_agent=UA, viewport={"width": 1366, "height": 900}, accept_downloads=False,
                                          ignore_https_errors=True, locale="ko-KR")
                ctx.set_default_timeout(30000)
                # 씨앗 주소가 다른 등록 도메인으로 3xx 리디렉트하는지 먼저 본다(리디렉트를 따라가지 않음)
                try:
                    r0 = ctx.request.get(url, max_redirects=0, timeout=20000, headers={"User-Agent": UA})
                    if 300 <= r0.status < 400:
                        loc = urljoin(url, r0.headers.get("location", ""))
                        if reg_domain(loc) != site:
                            rec.update(status=f"redirect_offsite:{r0.status}", final_url=loc)
                            ctx.close()
                            pag.row(rec)
                            time.sleep(DELAY)
                            continue
                except Exception as e:
                    rec["error"] = f"probe:{type(e).__name__}"

                bodies = {}

                def on_route(route):
                    req = route.request
                    try:
                        if req.is_navigation_request() and not req.url.startswith(("about:", "data:", "blob:")):
                            fr = req.frame
                            if reg_domain(req.url) != site:
                                if fr.parent_frame is None:
                                    cnt["blocked_nav"] += 1
                                else:
                                    cnt["blocked_iframe"] += 1
                                return route.abort()
                    except Exception:
                        pass
                    return route.continue_()

                def on_response(resp):
                    try:
                        if resp.request.resource_type == "image" and resp.ok:
                            b = resp.body()
                            if len(b) <= MAX_BYTES:
                                bodies[resp.url] = (b, resp.headers.get("content-type", ""))
                    except Exception:
                        pass

                ctx.route("**/*", on_route)
                page = ctx.new_page()
                ctx.on("page", lambda pg: pg.close())  # 이 뒤에 열리는 창(팝업)은 바로 닫는다
                page.on("response", on_response)
                resp = page.goto(url, wait_until="load", timeout=40000)
                rec["status"] = str(resp.status) if resp else "no_response"
                page.wait_for_timeout(1500)
                # 지연 로딩 이미지를 깨우려고 끝까지 내려간다(최대 12번)
                for _ in range(12):
                    at_end = page.evaluate("() => { window.scrollBy(0, window.innerHeight); return window.scrollY + window.innerHeight >= document.body.scrollHeight - 5; }")
                    page.wait_for_timeout(400)
                    if at_end:
                        break
                page.wait_for_timeout(1500)
                rec["final_url"] = page.url
                if reg_domain(page.url) != site:  # 혹시 이동이 새어 나갔으면 기록만 하고 수집하지 않는다
                    rec["status"] = "left_site"
                    ctx.close()
                    pag.row(rec)
                    continue
                rec["title"] = (page.title() or "")[:200]
                text = page.evaluate("() => document.body ? document.body.innerText : ''") or ""
                rec["text_len"] = len(text)
                rec["gamble_hits"] = len(GAMBLE.findall(rec["title"] + " " + text[:50000]))
                txt.write(json.dumps({"page_url": url, "title": rec["title"], "text": text[:30000]}, ensure_ascii=False) + "\n")
                txt.flush()

                elems = []
                for fr in page.frames:
                    if fr != page.main_frame and reg_domain(fr.url) != site:
                        continue
                    try:
                        for e in fr.evaluate(IMG_JS):
                            e["frame"] = "" if fr == page.main_frame else fr.url
                            elems.append(e)
                    except Exception:
                        pass
                cnt["n_elems"] = len(elems)

                seen_url = {}
                for e in elems:
                    src = e["url"]
                    if src.startswith("data:") and not src.startswith("data:image"):
                        continue
                    if src not in seen_url:
                        seen_url[src] = fetch_one(src, url, bodies, ctx, svg_page, img_dir, adult_sha, skp, fail, cnt)
                    got = seen_url[src]
                    if not got:
                        continue
                    sha, fname, w, h = got
                    occ.row(dict(sha1=sha, file=f"images/{fname}", source_url=src if not src.startswith("data:") else "data-uri",
                                 page_url=url, site=site, site_type=site_type, element=e["element"], w=w, h=h,
                                 render_w=e["render_w"], render_h=e["render_h"], x=e["x"], y=e["y"], selector=e["selector"],
                                 link_href=e["link_href"], alt=e["alt"][:300], frame=e["frame"], collected_at=now()))
                    cnt["n_saved"] += 1
                ctx.close()
            except Exception as ex:
                rec["error"] = (rec.get("error", "") + f" {type(ex).__name__}:{str(ex)[:150]}").strip()
                try:
                    ctx.close()
                except Exception:
                    pass
            rec.update(cnt)
            pag.row(rec)
            print(f"[{args.shard}:{k + 1}/{len(seeds)}] {rec['status']} elems={cnt['n_elems']} saved={cnt['n_saved']} new={cnt['n_new']} "
                  f"adult={cnt['n_adult']} gamble={rec['gamble_hits']} {url[:90]}", flush=True)
            time.sleep(DELAY)
        browser.close()


def fetch_one(src, page_url, bodies, ctx, svg_page, img_dir, adult_sha, skp, fail, cnt):
    """이미지 하나를 얻어 거르고 저장한다. -> (sha1, 파일 이름, w, h) 또는 None."""
    import base64
    try:
        if src.startswith("data:image"):
            head, b64 = src.split(",", 1)
            data, ctype = (base64.b64decode(b64) if ";base64" in head else b64.encode()), head[5:].split(";")[0]
        elif src in bodies:
            data, ctype = bodies[src]
        else:
            if not robots_ok(src):
                fail.row(dict(page_url=page_url, source_url=src, reason="robots_disallow"))
                cnt["n_fail"] += 1
                return None
            r = ctx.request.get(src, max_redirects=0, timeout=15000, headers={"Referer": page_url, "User-Agent": UA})
            if not r.ok:
                fail.row(dict(page_url=page_url, source_url=src, reason=f"http_{r.status}"))
                cnt["n_fail"] += 1
                return None
            data, ctype = r.body(), r.headers.get("content-type", "")
            time.sleep(0.2)
        if len(data) > MAX_BYTES:
            fail.row(dict(page_url=page_url, source_url=src, reason="too_large"))
            cnt["n_fail"] += 1
            return None
        save, ext, first = decode(data, ctype, src, svg_page)
    except Exception as ex:
        fail.row(dict(page_url=page_url, source_url=src[:500], reason=f"decode:{type(ex).__name__}"))
        cnt["n_fail"] += 1
        return None
    w, h = first.size
    if w < MIN_SIDE or h < MIN_SIDE:
        skp.row(dict(page_url=page_url, source_url=src[:500], reason="too_small"))
        cnt["n_small"] += 1
        return None
    sha = hashlib.sha1(save).hexdigest()
    fname = f"{sha[:16]}.{ext}"
    path = os.path.join(img_dir, fname)
    if sha in adult_sha:
        skp.row(dict(page_url=page_url, source_url=src[:500], reason="adult"))
        cnt["n_adult"] += 1
        return None
    if not os.path.exists(path) or os.path.getsize(path) == 0:  # 크기 0 은 전원 차단으로 비어 버린 파일이다
        if nsfw.is_adult(first):
            adult_sha.add(sha)
            skp.row(dict(page_url=page_url, source_url=src[:500], reason="adult"))
            cnt["n_adult"] += 1
            return None
        tmp = path + f".tmp{os.getpid()}"
        with open(tmp, "wb") as f:
            f.write(save)
        os.replace(tmp, path)
        cnt["n_new"] += 1
    return sha, fname, w, h


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--shard", type=int, default=0)
    ap.add_argument("--nshards", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--file-shard", type=int, default=None, help="출력 파일 접미사 번호(기본은 --shard). 추가 수집용")
    a = ap.parse_args()
    random.seed(0)
    crawl(a)
