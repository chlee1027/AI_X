"""M3: 바탕 모델 점수가 애매한 구간에 든 이미지만 Claude 비전에 다시 묻는다.

검증셋(채현)
  python m3_claude.py $A --config configs/m3.yaml --base runs/m2/pred_m2_val.csv \
      --images <H4_trainval 폴더> [--dry-run] [--limit 20]
  - 가장 넓은 구간(widest_zone)의 이미지를 한 번만 묻고 답을 runs/m3/claude_cache.jsonl 에 쌓는다.
    다시 돌리면 이미 물은 이미지는 건너뛴다(같은 프롬프트·모델·설정일 때).
  - 그 안의 작은 구간(zone_lo x zone_hi)마다 fix(바탕이 틀렸는데 M3 가 맞힘)·break(바탕이 맞았는데 M3 가 틀림)·
    순이득·호출 수·비용을 다시 계산하고, select_rule 로 구간 하나를 고른다.
  - --dry-run 은 API 를 부르지 않고 구간별 호출 수와 예상 비용만 낸다. --limit N 은 무작위 N장만 묻는다(장당 비용 재기).

평가셋(준아, H7 뒤)
  python m3_claude.py $A --config configs/m3.yaml --base pred_<바탕>_test.csv --images <평가 이미지 폴더> \
      --allow-test --zone <lo> <hi> --out runs_test
  - 고른 구간 하나만 묻는다. 정답 라벨을 쓰지 않는다.

점수: 구간 밖은 바탕 점수 그대로. 구간 안은 lo + illegal_prob x (hi - lo) 로 바꿔 순위를 Claude 쪽으로 다시 매긴다.
pred: 구간 밖은 바탕 pred, 구간 안은 Claude 의 label == illegal. API 가 끝내 실패하거나 거절하면 바탕 pred 를 그대로 둔다.
"""
import argparse
import base64
import hashlib
import io
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, precision_recall_fscore_support

import imgcommon as C

SCHEMA = {
    "type": "object",
    "properties": {
        "label": {"type": "string", "enum": ["illegal", "legal_ad", "campaign", "normal"]},
        "illegal_prob": {"type": "number"},
        "subtype": {"type": "string", "enum": ["gambling", "fake_doc", "adult", "sim_loan", "drug",
                                               "illegal_loan", "other", "none"]},
        "evidence": {"type": "string"},
    },
    "required": ["label", "illegal_prob", "subtype", "evidence"],
    "additionalProperties": False,
}
MEDIA = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp", "gif": "image/gif"}
MAX_BYTES = 4_500_000          # API 한 장 한도(5MB) 아래로


# ---------- 이미지 ----------
def encode_image(path, max_side):
    """긴 변을 max_side 로 줄이고 base64 로. GIF 는 첫 장만 PNG 로 보낸다. (media_type, data, w, h)"""
    from PIL import Image
    raw = Path(path).read_bytes()
    ext = Path(path).suffix.lower().lstrip(".")
    im = Image.open(io.BytesIO(raw))
    w, h = im.size
    need = ext == "gif" or max(w, h) > max_side or len(raw) > MAX_BYTES or ext not in MEDIA
    if not need:
        return MEDIA[ext], base64.standard_b64encode(raw).decode(), w, h
    im.seek(0)
    im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
    if max(w, h) > max_side:
        r = max_side / max(w, h)
        im = im.resize((max(1, round(w * r)), max(1, round(h * r))), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "PNG", optimize=True)
    media = "image/png"
    if buf.tell() > MAX_BYTES:
        buf = io.BytesIO()
        im.convert("RGB").save(buf, "JPEG", quality=90)
        media = "image/jpeg"
    return media, base64.standard_b64encode(buf.getvalue()).decode(), im.size[0], im.size[1]


def est_image_tokens(w, h, max_side):
    r = min(1.0, max_side / max(w, h))
    return int(np.ceil((w * r) * (h * r) / 750))


# ---------- Claude ----------
def make_client(cfg):
    import anthropic
    # brotli 응답을 받지 않는다: Brotli 1.0.x 가 깔린 환경(anaconda 기본)에서는 httpx2 가 응답을 못 풀어
    # TypeError 가 APIConnectionError 로 보인다(11.13 채현 PC). gzip 은 표준 라이브러리라 어디서나 풀린다.
    return anthropic.Anthropic(max_retries=int(cfg.get("max_retries", 4)), timeout=120.0,
                               default_headers={"Accept-Encoding": "gzip, deflate"})


def ask(client, cfg, system, media, data, ocr_text):
    """이미지 한 장을 묻는다. 결과 dict(ok, label, illegal_prob, ..., usage, stop_reason, served_model)."""
    import anthropic
    content = [{"type": "image", "source": {"type": "base64", "media_type": media, "data": data}}]
    note = "이 이미지가 불법광고인지 판정해 주세요."
    if cfg.get("use_ocr_text", True):
        t = (ocr_text or "").strip()[: int(cfg.get("ocr_max_chars", 800))]
        note += f"\n\nOCR 글(참고용, 틀릴 수 있음): {t if t else '(없음)'}"
    content.append({"type": "text", "text": note})
    kw = dict(model=cfg["claude_model"], max_tokens=int(cfg.get("max_tokens", 4096)), system=system,
              messages=[{"role": "user", "content": content}],
              output_config={"effort": cfg.get("effort", "low"), "format": {"type": "json_schema", "schema": SCHEMA}})
    t0 = time.time()
    try:
        if cfg.get("fallback", True):
            r = client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kw)
        else:
            r = client.messages.create(**kw)
    except anthropic.BadRequestError as e:
        return {"ok": False, "error": f"bad_request: {e.message}"[:300]}
    except anthropic.AuthenticationError:
        raise SystemExit("API 키가 틀렸다(AuthenticationError). ANTHROPIC_API_KEY 를 확인")
    except anthropic.PermissionDeniedError:
        raise SystemExit("API 키 권한이 없다(PermissionDeniedError)")
    except anthropic.NotFoundError:
        raise SystemExit(f"모델을 찾을 수 없다: {cfg['claude_model']}")
    except anthropic.RateLimitError:
        return {"ok": False, "error": "rate_limit (재시도 뒤에도)"}
    except anthropic.APIStatusError as e:
        return {"ok": False, "error": f"status {e.status_code}"}
    except anthropic.APIConnectionError:
        return {"ok": False, "error": "connection"}
    u = r.usage
    out = {"stop_reason": r.stop_reason, "served_model": r.model, "sec": round(time.time() - t0, 2),
           "in_tok": int(u.input_tokens or 0) + int(u.cache_read_input_tokens or 0) + int(u.cache_creation_input_tokens or 0),
           "out_tok": int(u.output_tokens or 0)}
    if r.stop_reason == "refusal":
        cat = getattr(getattr(r, "stop_details", None), "category", None)
        return dict(out, ok=False, error=f"refusal:{cat}")
    if r.stop_reason == "max_tokens":
        return dict(out, ok=False, error="max_tokens")
    text = next((b.text for b in r.content if b.type == "text"), None)
    try:
        j = json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return dict(out, ok=False, error="bad_json")
    j["illegal_prob"] = float(min(1.0, max(0.0, j.get("illegal_prob", 0.0))))
    return dict(out, ok=True, **j)


def cost(rec, cfg):
    p = cfg["price_per_mtok"]
    return (rec.get("in_tok", 0) * p["input"] + rec.get("out_tok", 0) * p["output"]) / 1e6


# ---------- 캐시 ----------
def cache_key(cfg, prompt_hash):
    keys = ("claude_model", "effort", "max_tokens", "fallback", "use_ocr_text", "ocr_max_chars", "max_side")
    return hashlib.sha1(json.dumps([prompt_hash] + [cfg.get(k) for k in keys]).encode()).hexdigest()[:12]


FINAL_ERRORS = ("refusal", "bad_json", "max_tokens", "bad_request")   # 다시 물어도 같을 가능성이 커서 다시 묻지 않는다


def is_final(r):
    return bool(r.get("ok")) or str(r.get("error", "")).startswith(FINAL_ERRORS)


def read_cache(path, key):
    """(끝난 답, 다시 물을 실패). 끝난 답 = 성공 + 거절·형식 오류처럼 다시 물어도 같을 것."""
    done, retry = {}, {}
    if Path(path).exists():
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            r = json.loads(line)
            if r.get("key") != key:
                continue
            if is_final(r):
                if r.get("ok") or r["image_id"] not in done:
                    done[r["image_id"]] = r
            else:
                retry[r["image_id"]] = r
    return done, {k: v for k, v in retry.items() if k not in done}


def run_queries(df_q, cfg, system, key, cache_path, images_root):
    client = make_client(cfg)
    lock = threading.Lock()
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    def one(row):
        media, data, w, h = encode_image(Path(images_root) / row["file"], int(cfg.get("max_side", 1568)))
        rec = ask(client, cfg, system, media, data, row["text"])
        rec.update(image_id=row["image_id"], key=key, w=w, h=h)
        with lock, open(cache_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    rows = df_q.to_dict("records")
    out, t0 = [], time.time()
    with ThreadPoolExecutor(max_workers=int(cfg.get("workers", 6))) as ex:
        futs = [ex.submit(one, r) for r in rows]
        for i, fu in enumerate(as_completed(futs), 1):
            out.append(fu.result())
            if i % 20 == 0 or i == len(rows):
                c = sum(cost(r, cfg) for r in out)
                print(f"  {i}/{len(rows)}장, 지금까지 ${c:.3f}, {time.time() - t0:.0f}초", flush=True)
    return out


# ---------- 구간 계산 ----------
def apply_zone(base_score, base_pred, ans, lo, hi):
    """구간 [lo, hi) 안이고 답이 있는 이미지만 Claude 쪽으로 바꾼다."""
    s, p = base_score.copy(), base_pred.copy()
    inz = (base_score >= lo) & (base_score < hi)
    has = ans["ok"].map(lambda v: v is True).to_numpy()
    m = inz & has
    s[m] = lo + ans["illegal_prob"].to_numpy(dtype=float)[m] * (hi - lo)
    p[m] = (ans["label"].to_numpy() == "illegal")[m].astype(int)
    return s, p, inz


def score_zone(d, s, p, inz, cfg, costs):
    sc = d["scored"].to_numpy()
    y = d["y"].to_numpy()
    bp = d["base_pred"].to_numpy()
    fix = int(((bp != y) & (p == y) & sc).sum())
    brk = int(((bp == y) & (p != y) & sc).sum())
    pr, rc, f1, _ = precision_recall_fscore_support(y[sc], p[sc], average="binary", zero_division=0)
    human = d["labeler"].isin(["채현", "정연"]).to_numpy() | d["labeler"].str.contains("확인").to_numpy()
    hf = int(((bp != y) & (p == y) & sc & human).sum())
    hb = int(((bp == y) & (p != y) & sc & human).sum())
    return {"calls": int(inz.sum()), "cost_usd": round(float(costs[inz].sum()), 4), "fix": fix, "break": brk,
            "net": fix - brk, "fix_human": hf, "break_human": hb, "precision": round(pr, 4), "recall": round(rc, 4),
            "f1": round(f1, 4), "pr_auc": round(float(average_precision_score(y[sc], s[sc])), 4)}


def pick(zones):
    z = sorted(zones, key=lambda r: (-r["net"], r["calls"], r["hi"] - r["lo"]))
    return z[0]


# ---------- 메인 ----------
def main():
    ap = C.data_args(argparse.ArgumentParser())
    ap.add_argument("--base", required=True, help="바탕 모델 예측 CSV (image_id, score, pred)")
    ap.add_argument("--images", required=True, help="meta 의 file 열(images/...)이 이 폴더 기준")
    ap.add_argument("--allow-test", action="store_true")
    ap.add_argument("--zone", nargs=2, type=float, default=None, help="평가셋: 고른 구간 lo hi")
    ap.add_argument("--dry-run", action="store_true", help="API 를 부르지 않고 호출 수·예상 비용만")
    ap.add_argument("--limit", type=int, default=None, help="가장 넓은 구간에서 무작위 N장만 묻는다(시드 0)")
    a = ap.parse_args()
    cfg, chash = C.load_config(a.config)
    commit = C.git_commit()
    prompt = (C.HERE / cfg["prompt"]).read_text(encoding="utf-8")
    phash = hashlib.sha1(prompt.encode()).hexdigest()[:12]
    key = cache_key(cfg, phash)
    out = Path(a.out) / cfg["model_id"]
    cache_path = out / "claude_cache.jsonl"

    df = C.load(a.split, a.meta, a.ocr, allow_test=a.allow_test)
    split = "test" if a.allow_test else "val"
    df = df[df["split"] == split].reset_index(drop=True)
    base = pd.read_csv(a.base, dtype={"image_id": str})[["image_id", "score", "pred"]]
    base = base.rename(columns={"score": "base_score", "pred": "base_pred"})
    d = df.merge(base, on="image_id", how="left", validate="1:1")
    # 바탕 점수 파일이 unsure == 1(채점 제외) 이미지를 뺀 채 올 수 있다(다영 M2 검증 점수). 그런 행만 빼고 묻지 않는다.
    miss = d["base_score"].isna()
    if (miss & d["scored"]).any():
        raise SystemExit(f"바탕 점수가 없는 채점 대상 {split} 이미지 {int((miss & d['scored']).sum())}장")
    if miss.any():
        print(f"[알림] 바탕 점수가 없는 채점 제외(unsure) 이미지 {int(miss.sum())}장은 빼고 묻지 않는다")
        d = d[~miss].reset_index(drop=True)
        d["base_pred"] = d["base_pred"].astype(int)
    thr = float(d.loc[d["base_pred"] == 1, "base_score"].min())
    lo_w, hi_w = (a.zone if a.zone else cfg["widest_zone"])
    if not (lo_w < thr < hi_w):
        raise SystemExit(f"구간 [{lo_w}, {hi_w}) 이 바탕 문턱 {thr:.4f} 를 감싸지 않는다")
    q = d[(d["base_score"] >= lo_w) & (d["base_score"] < hi_w)]
    print(f"[{split}] {len(d)}장, 바탕 {cfg['base_model_id']} 문턱 {thr:.4f}, 구간 [{lo_w}, {hi_w}) {len(q)}장")
    if a.limit:
        q = q.sample(n=min(a.limit, len(q)), random_state=0)
        print(f"  --limit: 무작위 {len(q)}장만 묻는다")

    if a.dry_run:
        from PIL import Image
        ms = int(cfg.get("max_side", 1568))
        toks = [est_image_tokens(*Image.open(Path(a.images) / f).size, ms) for f in q["file"]]
        sys_tok = len(prompt) // 2          # 한국어는 대략 글자 2개에 토큰 1개로 어림
        p = cfg["price_per_mtok"]
        est_in = np.array(toks) + sys_tok + 300
        est_out = 600                        # thinking 포함 어림값. --limit 시범 실행으로 실제 값을 잰다
        per = (est_in * p["input"] + est_out * p["output"]) / 1e6
        print(f"  어림 입력 토큰 장당 중앙값 {int(np.median(est_in))}, 출력 {est_out} 로 놓으면"
              f" 장당 ${np.median(per):.4f}, {len(q)}장 ${per.sum():.2f} ({cfg['claude_model']})")
        if not a.zone:
            for lo in cfg["zone_lo"]:
                print("   lo", lo, " ".join(f"hi{hi}:{int(((d.base_score >= lo) & (d.base_score < hi)).sum())}"
                                         for hi in cfg["zone_hi"]))
        return

    done, failed = read_cache(cache_path, key)
    todo = q[~q["image_id"].isin(done)]
    print(f"  캐시에 끝난 답 {len(done)}장, 새로 물을 것 {len(todo)}장 (전에 일시 오류로 실패한 {len(set(failed) & set(todo.image_id))}장 포함)")
    for r in run_queries(todo, cfg, prompt, key, cache_path, a.images):
        if is_final(r):
            done[r["image_id"]] = r
        else:
            failed[r["image_id"]] = r
    recs = {i: done.get(i) or failed.get(i) for i in q["image_id"]}
    ans = pd.DataFrame([dict(image_id=i, **{k: (r or {}).get(k) for k in ("ok", "label", "illegal_prob", "error",
                        "served_model", "in_tok", "out_tok")}) for i, r in recs.items()])
    ans = d[["image_id"]].merge(ans, on="image_id", how="left")
    costs = np.array([cost(r, cfg) if isinstance(r, dict) else 0.0 for r in
                      ans.apply(lambda x: recs.get(x.image_id), axis=1)])
    n_ok = int(ans["ok"].map(lambda v: v is True).sum())
    errs = ans.loc[ans["ok"] == False, "error"].value_counts().to_dict()  # noqa: E712
    asked = ans["ok"].notna()
    print(f"  답 {n_ok}장, 실패 {int((ans['ok'] == False).sum())}장 {errs}, "  # noqa: E712
          f"비용 ${costs.sum():.3f} (장당 ${costs[asked].mean() if asked.any() else 0:.4f})")
    served = ans["served_model"].dropna().value_counts().to_dict()
    if served:
        print("  답한 모델:", served)

    bs, bp = d["base_score"].to_numpy(float), d["base_pred"].to_numpy(int)
    if a.allow_test:
        s, p, inz = apply_zone(bs, bp, ans, lo_w, hi_w)
        pd.DataFrame({"image_id": d["image_id"], "score": np.round(s, 6), "pred": p, "model_id": cfg["model_id"],
                      "config_hash": chash, "commit": commit})[C.PRED_COLS].to_csv(out / f"pred_{cfg['model_id']}_test.csv", index=False)
        C.save_json(out / f"report_{cfg['model_id']}_test.json", {"zone": [lo_w, hi_w], "calls": int(inz.sum()),
                    "answered": n_ok, "errors": errs, "cost_usd": round(float(costs.sum()), 4), "served": served,
                    "prompt_hash": phash, "config_hash": chash, "commit": commit})
        print(f"결과: {out}")
        return

    if a.limit:
        print("  --limit 시범 실행이라 구간 고르기는 하지 않는다. 장당 비용만 본다")
        return
    base_m = score_zone(d, bs, bp, np.zeros(len(d), bool), cfg, costs)
    print(f"  바탕만: P {base_m['precision']} R {base_m['recall']} F1 {base_m['f1']} PR-AUC {base_m['pr_auc']}")
    zones = []
    for lo in cfg["zone_lo"]:
        for hi in cfg["zone_hi"]:
            if not (lo_w <= lo < thr < hi <= hi_w):
                continue
            s, p, inz = apply_zone(bs, bp, ans, lo, hi)
            zones.append(dict(lo=lo, hi=hi, **score_zone(d, s, p, inz, cfg, costs)))
    zt = pd.DataFrame(zones)
    out.mkdir(parents=True, exist_ok=True)
    zt.to_csv(out / f"zones_{cfg['model_id']}_val.csv", index=False)
    best = pick(zones)
    print(zt.to_string(index=False))
    print(f"  고른 구간 [{best['lo']}, {best['hi']}): 순이득 {best['net']} (fix {best['fix']}, break {best['break']}),"
          f" 호출 {best['calls']}장, ${best['cost_usd']}")
    s, p, inz = apply_zone(bs, bp, ans, best["lo"], best["hi"])
    pd.DataFrame({"image_id": d["image_id"], "score": np.round(s, 6), "pred": p, "model_id": cfg["model_id"],
                  "config_hash": chash, "commit": commit})[C.PRED_COLS].to_csv(out / f"pred_{cfg['model_id']}_val.csv", index=False)
    rate = best["calls"] / len(d)
    C.save_json(out / f"report_{cfg['model_id']}.json", {
        "base_model_id": cfg["base_model_id"], "base_threshold": thr, "base_val": base_m, "chosen": best,
        "select_rule": cfg["select_rule"], "call_rate_val": round(rate, 4), "answered": n_ok, "errors": errs,
        "served": served, "cost_per_image_usd": round(float(costs[asked].mean()), 5) if asked.any() else None,
        "prompt_hash": phash, "cache_key": key, "config_hash": chash, "commit": commit})
    C.log_experiment(out.parent / "experiments.csv", dict(
        exp_id=C.exp_id(cfg["model_id"], 0), model_id=cfg["model_id"], config=a.config, config_hash=chash, seed=0,
        split="val", n=int(d["scored"].sum()), n_pos=int(d.loc[d["scored"], "y"].sum()), precision=best["precision"],
        recall=best["recall"], f1=best["f1"], pr_auc=best["pr_auc"], threshold="", commit=commit,
        memo=f"base={cfg['base_model_id']} zone=[{best['lo']},{best['hi']}) net={best['net']} calls={best['calls']} "
             f"prompt={phash} {cfg['claude_model']} effort={cfg.get('effort')}"))
    print(f"결과: {out}")


if __name__ == "__main__":
    main()
