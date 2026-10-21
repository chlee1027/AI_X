"""봉인 시험셋 추가 유형(ETC) 채점 (10-21, 진행보고서 7-86절). 사용자가 직접 돌린다. 집계만 출력한다(표본 내용·id 는 내지 않음).

시험셋 폴더(dev_data 와 같은 구조)의 조각을 한 쪽씩 그려, 제출 실행 파일과 같은 길(scan4.fetch -> 규칙·거르개 -> 광고 점수
-> [API 판정] -> extra.judge_rows(글자 변형) + extra.judge(DOM 갈래))로 result_extra.json 에 들어갈 검출을 만든다.
  - 양성: etc/etc.yaml(갈래 하나, extra_finding), combo/combo_real.yaml(갈래 여러 개, extra_findings, 빈 것은 뺌)
  - 음성: decoy/decoy.yaml, offscreen/offscreen_real_negative.yaml, transparent/transparent_real_negative.yaml (있는 것만)
맞음 = 예측 선택자가 정답 위치(expected_location)와 같은 요소. 점수는 (45 x 재현율 + 35 x 정밀도) / 80.
  - [위치+갈래] 정답 단위 (표본, 갈래). 예측 단위 (표본, 위치, 갈래). 위치가 맞고 갈래가 그 표본 정답 갈래에 있으면 맞음
  - [위치만] 갈래 이름은 보지 않는다(요강 채점이 갈래 이름까지 보는지 모르므로 둘 다 적는다)
이 채점기는 시험셋을 처음 ETC 에 쓰는 것이다. 결과를 보고 규칙·문턱을 고치지 않는다(고치면 시험셋이 진단용이 된다).

사용: python score_test_etc.py --test <시험셋 폴더> [--run runs/v9n] [--api] [--workers 4]
     --api 를 주면 제출 API 판과 같이 Haiku 에 묻는다(키: 환경변수 ANTHROPIC_API_KEY 또는 .env, 없으면 API 없이 돈다)
     개발 데이터로 돌아가는지만 볼 때: python score_test_etc.py --test ../dev_data --limit 20
"""
import argparse
import os
import pickle
import queue
import sys
import threading
import time
from collections import Counter
from pathlib import Path

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "8")
HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent / "model")]
os.environ.setdefault("ADDETECTOR_HOME", str(HERE.parent / "package" / "dist" / "AdDetector_API"))  # 키(.env) 찾을 곳
import yaml  # noqa: E402
import rules4  # noqa: E402

rules4.use()
import scan4  # noqa: E402
import extra as extra_mod  # noqa: E402

URL = "http://dev.test/"
SAME = """([a, b]) => { try { const x = document.querySelectorAll(a), y = document.querySelectorAll(b);
  return x.length === 1 && y.length === 1 && x[0] === y[0]; } catch (e) { return false; } }"""
POS = (("etc", "etc/etc.yaml"), ("combo", "combo/combo_real.yaml"))
NEG = (("decoy", "decoy/decoy.yaml"), ("offscreen_neg", "offscreen/offscreen_real_negative.yaml"),
       ("transparent_neg", "transparent/transparent_real_negative.yaml"))


def page_html(x):
    css = x.get("css") or ""
    h = x["html"]
    head = h if h.lstrip().lower().startswith(("<meta", "<title")) else ""
    body = "" if head else h
    return f"<!doctype html><html><head><meta charset='utf-8'><style>{css}</style>{head}</head><body>{body}</body></html>"


def load(root, limit):
    items = []
    for src, f in POS:
        p = root / f
        if not p.exists():
            continue
        for x in yaml.safe_load(open(p, encoding="utf-8")) or []:
            want = x.get("extra_findings") if "extra_findings" in x else [x.get("extra_finding")]
            want = sorted({w for w in (want or []) if w})
            if want and x.get("is_positive", True) and x.get("expected_location"):
                items.append((src, x, want))
    for src, f in NEG:
        p = root / f
        if p.exists():
            items += [(src, x, []) for x in yaml.safe_load(open(p, encoding="utf-8")) or []]
    if limit:  # 개발 데이터로 동작만 볼 때. 출처별로 앞에서 limit 개
        cnt, keep = Counter(), []
        for it in items:
            if cnt[it[0]] < limit:
                keep.append(it)
                cnt[it[0]] += 1
        items = keep
    return items


def predict(fx, model, judge, lock):
    """scan4.scan 의 process() 중 추가 유형 부분과 같은 순서. [(갈래, 선택자)]"""
    out = []
    rows, eitems = fx["rows"], fx["eitems"]
    with lock:  # 판정기·API 판정은 한 번에 하나
        if rows:
            scan4.rule_cache(rows)
            if getattr(model, "ui", False):
                scan4.ui_skip(rows)
            if getattr(model, "stack", False):
                rules4.stack_skip(rows)
            if getattr(model, "garble", False):
                rules4.garble_skip(rows)
            ad = model.ad.score(rows)
            if getattr(model, "conj_strong", False):
                ad = rules4.conj_boost(rows, ad, getattr(model, "conj_floor", 0.99))
            if judge is not None:
                ad = judge.adjust(rows, ad, model.thr)
            out += [(t, sel) for t, sel, *_ in extra_mod.judge_rows(rows, ad)]
        out += [(t, sel) for t, sel, *_ in extra_mod.judge(eitems, model, fx["final"], judge if getattr(judge, "wide", False) else None)]
    return sorted(set(out))


def worker(jobs, results, model, judge, lock):
    from playwright.sync_api import sync_playwright
    cur = {"html": ""}
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True)
        pg = b.new_page()
        # 조각 안 외부 그림·글꼴은 막는다(eval_extra.py 와 같음)
        pg.route("**/*", lambda r: r.fulfill(status=200, content_type="text/html; charset=utf-8", body=cur["html"])
                 if r.request.url.startswith(URL) else r.abort())
        while True:
            try:
                k, (src, x, want) = jobs.get_nowait()
            except queue.Empty:
                break
            cur["html"] = page_html(x)
            try:
                fx = scan4.fetch(pg, URL)
                if fx.get("error"):
                    results.put((k, src, want, None, fx["error"]))
                    continue
                preds = predict(fx, model, judge, lock)
                hit = [(t, sel, bool(want) and bool(pg.evaluate(SAME, [sel, x["expected_location"]]))) for t, sel in preds]
                results.put((k, src, want, hit, None))
            except Exception as e:
                results.put((k, src, want, None, f"{type(e).__name__}: {str(e)[:80]}"))
        b.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--test", required=True)
    ap.add_argument("--run", default="runs/v9n")
    ap.add_argument("--api", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    model = pickle.load(open(HERE / a.run / "model.pkl", "rb"))
    for k in ("hg2", "jl_both", "numform"):  # scan4.scan 과 같게 모델 표지로 규칙 옵션을 켠다
        rules4.OPTS[k] = bool(getattr(model, k, False))
    judge = None
    if a.api:
        from llm_judge import Judge2
        judge = Judge2(model="claude-haiku-5-5", wide=True, recheck=False, log=lambda *x: None)  # 제출 API 판 설정과 같음
        if not judge.key:
            print("[API] 키가 없어 API 없이 돈다")
            judge = None
    items = load(Path(a.test), a.limit)
    print(f"표본: { {s: n for s, n in Counter(s for s, *_ in items).items()} } (모델 {a.run}, API {'켬' if judge else '끔'})", flush=True)
    jobs, results, lock = queue.Queue(), queue.Queue(), threading.Lock()
    for k, it in enumerate(items):
        jobs.put((k, it))
    t0 = time.time()
    ths = [threading.Thread(target=worker, args=(jobs, results, model, judge, lock), daemon=True) for _ in range(max(1, a.workers))]
    for th in ths:
        th.start()
    gold_n, gold_hit = Counter(), Counter()          # (갈래) 정답 단위 수 / 맞힘
    pred_n, pred_ok = Counter(), Counter()           # (갈래) 예측 수 / 맞은 예측 수
    loc_pos, loc_hit = 0, 0                          # 위치만: 양성 표본 수 / 위치 맞힌 표본 수
    loc_pred, loc_ok = 0, 0                          # 위치만: 예측 요소 수 / 위치 맞은 예측 수
    neg_n, neg_fp = Counter(), Counter()             # 음성 출처별 표본 수 / 낸 건수(갈래별)
    err, done = Counter(), 0
    while done < len(items):
        try:
            k, src, want, hit, e = results.get(timeout=5)
        except queue.Empty:
            if not any(th.is_alive() for th in ths):
                break
            continue
        done += 1
        if done % 50 == 0:
            print(f"  {done}/{len(items)}  {time.time() - t0:.0f}초", flush=True)
        if e is not None:
            err[src] += 1
            hit = []
        if want:
            loc_pos += 1
            for w in want:
                gold_n[w] += 1
                if any(ok and t == w for t, _, ok in hit):
                    gold_hit[w] += 1
            loc_hit += any(ok for *_, ok in hit)
        else:
            neg_n[src] += 1
            for t, *_ in hit:
                neg_fp[(src, t)] += 1
        for t, _, ok in hit:
            pred_n[t] += 1
            pred_ok[t] += ok and t in want
        el = {}  # 위치만: 같은 요소를 여러 갈래로 낸 것은 한 건
        for _, sel, ok in hit:
            el[sel] = el.get(sel, False) or ok
        loc_pred += len(el)
        loc_ok += sum(el.values())

    def sc(r, p):
        return (45 * r + 35 * p) / 80

    G, H, P, O = sum(gold_n.values()), sum(gold_hit.values()), sum(pred_n.values()), sum(pred_ok.values())
    r, p = (H / G if G else 0), (O / P if P else 0)
    print(f"\n걸린 시간 {time.time() - t0:.0f}초, 실패 {dict(err) or 0}")
    print(f"[위치+갈래] 정답 {G}, 예측 {P}, 맞음(정답 쪽) {H} / 맞은 예측 {O}")
    print(f"  재현율 {r:.3f}  정밀도 {p:.3f}  점수 {sc(r, p):.3f}")
    print(f"  {'갈래':18s} {'정답':>5s} {'맞힘':>5s} {'예측':>5s} {'맞은 예측':>8s}")
    for t in sorted(set(gold_n) | set(pred_n), key=lambda t: -gold_n[t]):
        print(f"  {t:18s} {gold_n[t]:5d} {gold_hit[t]:5d} {pred_n[t]:5d} {pred_ok[t]:8d}")
    r2, p2 = (loc_hit / loc_pos if loc_pos else 0), (loc_ok / loc_pred if loc_pred else 0)
    print(f"[위치만] 양성 표본 {loc_pos} 중 위치 맞힘 {loc_hit}, 예측 {loc_pred} 중 위치 맞음 {loc_ok}")
    print(f"  재현율 {r2:.3f}  정밀도 {p2:.3f}  점수 {sc(r2, p2):.3f}")
    print(f"[음성] 표본 {dict(neg_n)}, 낸 건수 {sum(neg_fp.values())} {dict(neg_fp)}")
    if judge is not None:
        print("[API]", judge.summary())


if __name__ == "__main__":
    main()
