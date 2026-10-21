"""사이트 검사: 진입 URL 하나에서 같은 호스트 페이지를 따라가며 학습된 모델로 탐지하고 요강 형식 result.json 을 쓴다.

화면 특징은 학습 때와 같은 render.JS 를 페이지 전체(document.body)와 iframe 안에 그대로 돌려 얻는다.
선택자는 같은 호출 안에서 만든다(태그.클래스, 없으면 nth-of-type, 문서에서 1개를 가리킬 때까지 위로 붙임).
iframe 안 요소는 iframe[src="절대주소"] >>> 선택자 로 적는다.

사용: python site_scan.py --url <진입 URL> --run runs/A --out scans/A_site --max-pages 60 --minutes 10 [--delay 1.0]
"""
import argparse
import json
import os
import pickle
import sys
import time
from collections import deque
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse, urldefrag
from urllib import robotparser

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "8")
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import train  # noqa: E402,F401  (pickle 이 train.Model 을 찾도록)
from render import JS as RENDER_JS  # noqa: E402
from train import dense, decide  # noqa: E402
from common import MAIN4  # noqa: E402

MAX_CAND = 3000
PAGE_JS = "(args) => { const res = (" + RENDER_JS.replace("document.getElementById('root')", "document.body") + r""")(args);
  const all = Array.from(document.body.querySelectorAll('*'));
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
  for (const c of res.cands) c.sel = sel(all[c.i]);
  const links = Array.from(document.querySelectorAll('a[href]')).map(a => a.href);
  return {cands: res.cands, links};
}"""


def norm(u):
    return urldefrag(u)[0]


def scan(url, run, out, max_pages, minutes, delay):
    from playwright.sync_api import sync_playwright
    m = pickle.load(open(Path(run) / "model.pkl", "rb"))
    model, thr = m["model"], m["thresholds"]
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    kst = timezone(timedelta(hours=9))
    started = datetime.now(kst)
    t0 = time.time()
    host = urlparse(url).hostname
    rp = robotparser.RobotFileParser()
    try:
        rp.set_url(f"{urlparse(url).scheme}://{host}/robots.txt")
        rp.read()
    except Exception:
        rp = None
    seen, q, findings, pages = {norm(url)}, deque([url]), [], []
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        ctx = b.new_context(viewport={"width": 1280, "height": 800})
        pg = ctx.new_page()
        while q and len(pages) < max_pages and time.time() - t0 < minutes * 60:
            u = q.popleft()
            if rp is not None and not rp.can_fetch("*", u):
                continue
            try:
                pg.goto(u, wait_until="load", timeout=20000)
                pg.wait_for_timeout(300)
            except Exception as e:
                pages.append({"url": u, "error": str(e)[:120]})
                continue
            page_rows = []
            frames = [(pg.main_frame, "")]
            for fr in pg.frames[1:]:
                try:
                    src = fr.url
                    if src and src.startswith("http"):
                        frames.append((fr, f'iframe[src="{src}"] >>> '))
                except Exception:
                    pass
            links = []
            for fr, prefix in frames:
                try:
                    res = fr.evaluate(PAGE_JS, [MAX_CAND, []])
                except Exception:
                    continue
                if not prefix:
                    links = res["links"]
                for c in res["cands"]:
                    page_rows.append({"sid": u + "|" + prefix, "cat": "", "i": c["i"], "parent": c["parent"], "tag": c["tag"],
                                      "text": c["text"], "href": c.get("href", ""), "f": c["f"], "lab": {t: 0 for t in MAIN4},
                                      "t_skip": 0, "sel": prefix + c["sel"], "url": u})
            if page_rows:
                prob = model.predict(page_rows, dense(page_rows))
                hit = decide(page_rows, prob, thr)
                key = {(r["sid"], r["i"]): r for r in page_rows}
                for sid, i, t in sorted(hit):
                    r = key[(sid, i)]
                    k = page_rows.index(r)
                    findings.append({"url": r["url"], "is_violation": True, "location": r["sel"],
                                     "evidence_text": r["text"][:300], "technique": t, "_p": round(float(prob[t][k]), 3)})
            pages.append({"url": u, "cands": len(page_rows)})
            for l in links:
                l = norm(l)
                if urlparse(l).hostname == host and l not in seen and urlparse(l).scheme in ("http", "https"):
                    if not any(l.lower().endswith(x) for x in (".pdf", ".hwp", ".hwpx", ".zip", ".jpg", ".png", ".xlsx", ".doc", ".docx")):
                        seen.add(l)
                        q.append(l)
            time.sleep(delay)
        b.close()
    done = datetime.now(kst)
    uniq, outf = set(), []
    for f in findings:
        k = (f["url"], f["location"], f["technique"])
        if k in uniq:
            continue
        uniq.add(k)
        outf.append(dict(f, id=f"f_{len(outf) + 1:03d}"))
    result = {"meta": {"topic": "TOPIC", "entry_url": url, "started_at": started.isoformat(timespec="seconds"),
                       "finished_at": done.isoformat(timespec="seconds"), "elapsed_sec": round(time.time() - t0, 1),
                       "tool_version": "v2-" + m["code_sha256"][:8]},
              "findings": [{k: f[k] for k in ("id", "url", "is_violation", "location", "evidence_text", "technique")} for f in outf]}
    (out / "result.json").write_bytes(json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8"))
    (out / "debug.json").write_text(json.dumps({"pages": pages, "findings_with_prob": outf}, ensure_ascii=False, indent=2), encoding="utf-8")
    return result, pages


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--run", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-pages", type=int, default=60)
    ap.add_argument("--minutes", type=float, default=10)
    ap.add_argument("--delay", type=float, default=1.0)
    a = ap.parse_args()
    res, pages = scan(a.url, a.run, a.out, a.max_pages, a.minutes, a.delay)
    print(f"페이지 {len(pages)}쪽, 검출 {len(res['findings'])}건, {res['meta']['elapsed_sec']}초 -> {a.out}/result.json")


if __name__ == "__main__":
    main()
