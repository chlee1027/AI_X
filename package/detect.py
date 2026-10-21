"""공공 웹사이트 불법광고 탐지 도구 실행 파일 입구 (10-19).

요강 요구(진행보고서 1절): 진입 URL 하나를 넣으면 탐지하고, 구동 파일 폴더에 result.json 을 만든다. 30분을 넘으면 검출 시간 0점.
  - 검사 본체는 model2/scan4.py 의 scan() 을 그대로 쓴다(동결된 v8c 와 같은 판정).
  - 모델은 exe 옆 model_v9n 폴더(model.pkl)에서 읽는다. 모델만 바꿀 때는 다시 빌드하지 않고 폴더를 바꾸면 된다.
  - 시간 상한: 기본 20분 또는 2,000쪽 중 먼저 닿는 쪽에서 멈추고(10-21 사용자: 작은 사이트는 상한과 상관없이 빨리 끝나므로 2,000쪽, 2,000쪽이 약 17분이라 20분) result.json 을 쓴다(10-21, 진행보고서 7-68절. 동시 크롤링으로 400쪽이 3~4분이라
    큰 사이트도 대부분 보면서 검출 시간을 30분 상한의 절반 아래로 둔다. 예전 기본은 24분·400쪽).

사용: 탐지도구.exe <진입 URL> [--minutes 20] [--max-pages 2000] [--delay 0.2]
      URL 없이 실행하면 입력을 묻는다.
"""
import argparse
import os
import sys
import time
from pathlib import Path

FROZEN = getattr(sys, "frozen", False)
BASE = Path(sys.executable).parent if FROZEN else Path(__file__).resolve().parent
if not FROZEN:
    sys.path[:0] = [str(BASE.parent / "model2"), str(BASE.parent / "model")]
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "4")

import scan4  # noqa: E402
import report_html  # noqa: E402,F401  (빌드에 포함되도록)
import llm_judge  # noqa: E402,F401  (빌드에 포함되도록)


def write_empty(out, entry, t0):
    """검사가 실패해도 요강 스키마(meta + 빈 findings)에 맞는 result.json·result_extra.json 을 쓴다."""
    import json
    from datetime import datetime, timedelta, timezone
    kst = timezone(timedelta(hours=9))
    meta = {"topic": "TOPIC", "entry_url": entry, "started_at": datetime.fromtimestamp(t0, kst).isoformat(timespec="seconds"),
            "finished_at": datetime.now(kst).isoformat(timespec="seconds"), "elapsed_sec": round(time.time() - t0, 1),
            "tool_version": "AdDetector-error"}
    res = {"meta": meta, "findings": []}
    out.mkdir(parents=True, exist_ok=True)
    for name in ("result.json", "result_extra.json"):
        (out / name).write_bytes(json.dumps(res, ensure_ascii=False, indent=2).encode("utf-8"))
    return res


def main():
    ap = argparse.ArgumentParser(description="공공 웹사이트 불법광고 탐지")
    ap.add_argument("url", nargs="?")
    ap.add_argument("--minutes", type=float, default=20)
    ap.add_argument("--max-pages", type=int, default=2000)
    ap.add_argument("--delay", type=float, default=0.2)
    ap.add_argument("--model", default=str(BASE / "model_v9n"))
    ap.add_argument("--out", default=str(BASE))
    ap.add_argument("--no-open", action="store_true", help="결과 화면을 자동으로 열지 않음")
    ap.add_argument("--api", action="store_true", help="애매한 후보만 언어 모델에 2차 판정(키: ANTHROPIC_API_KEY 또는 exe 옆 api_key.txt)")
    ap.add_argument("--no-api", action="store_true", help="settings.json 이 API 를 켜 두었어도 끔")
    a = ap.parse_args()
    # 10-19: API 판과 API 없는 판은 같은 실행 파일이고, exe 옆 settings.json 의 "api" 값만 다르다(진행보고서 7-30절)
    settings = {}
    try:
        import json
        settings = json.loads((BASE / "settings.json").read_text(encoding="utf-8-sig"))
    except Exception:
        pass
    use_api = (a.api or settings.get("api", False)) and not a.no_api
    judge = None
    if use_api:
        os.environ.setdefault("ADDETECTOR_HOME", str(BASE))
        from llm_judge import Judge
        if settings.get("api_mode") == "v2":  # 10-21 API v2(진행보고서 7-65절): 맥락 + 확신 있을 때만
            from llm_judge import Judge2
            judge = Judge2(model=settings.get("api_model"), wide=bool(settings.get("api_wide", False)),  # 10-21 v2x(7-75절)
                           recheck=bool(settings.get("api_recheck", False)), model2=settings.get("api_model2"))  # v2r(7-80절)
        else:
            judge = Judge(mode=settings.get("api_mode"))  # "promote"·"both"·"demote", 진행보고서 7-30·7-44절
        print("[API 판] " + ("키 확인됨: 애매한 후보만 언어 모델에 묻습니다" if not judge.dead else f"{judge.dead}: API 없이 판정합니다"), flush=True)
    entry = (a.url or input("검사할 사이트 주소(URL)를 입력하세요: ")).strip()
    t0 = time.time()  # 10-21(진행보고서 7-83절): 요강 meta.started_at = URL 입력 시각, entry_url = 입력값 그대로
    url = entry if entry.startswith(("http://", "https://")) else "http://" + entry
    print(f"[탐지 시작] {url}  (최대 {a.minutes:g}분, {a.max_pages}쪽)", flush=True)
    try:
        res, pages = scan4.scan(url, a.model, a.out, a.max_pages, a.minutes, a.delay, "block", False, judge,
                                entry_url=entry, started_at=t0)
    except Exception as e:  # 10-21(7-83절): 어떤 오류가 나도 요강 스키마에 맞는 결과 파일은 남긴다(미생성 시 평가 제외)
        print(f"[오류] 검사 중 문제가 생겨 빈 결과를 씁니다: {type(e).__name__}: {e}", flush=True)
        res, pages = write_empty(Path(a.out), entry, t0), []  # 10-19 hedge -> inner(7-37절), 10-20 block(7-50절)
    by = {}
    for f in res["findings"]:
        by[f["technique"]] = by.get(f["technique"], 0) + 1
    print(f"[탐지 완료] 페이지 {len(pages)}쪽, 검출 {len(res['findings'])}건 {by}, {time.time() - t0:.1f}초", flush=True)
    print(f"결과 파일: {Path(a.out) / 'result.json'}", flush=True)
    try:  # 10-20 추가 유형(진행보고서 7-50절)
        import json
        xs = json.loads((Path(a.out) / "result_extra.json").read_text(encoding="utf-8"))["findings"]
        bx = {}
        for f in xs:
            bx[f["extra_finding"]] = bx.get(f["extra_finding"], 0) + 1
        print(f"추가 유형 결과 파일: {Path(a.out) / 'result_extra.json'}  ({len(xs)}건 {bx})", flush=True)
    except Exception:
        pass
    if judge is not None:
        sm = judge.summary()
        print(f"[API] 물은 글 {sm['asked']}개, 호출 {sm['calls']}번, {sm['seconds']}초, 토큰 입력 {sm['usage']['input_tokens']} / 출력 {sm['usage']['output_tokens']}"
              + (f" | 중단: {sm['fallback']}" if sm["fallback"] and sm["fallback"] != "API 키 없음" else ""), flush=True)
    try:  # 10-19: 결과 확인 화면(진행보고서 7-24절). 실패해도 result.json 은 이미 써 있다
        import report_html
        rp = report_html.build(Path(a.out) / "result.json")
        print(f"결과 화면: {rp}", flush=True)
        if not a.no_open:
            import webbrowser
            webbrowser.open(rp.resolve().as_uri())
    except Exception as e:
        print(f"결과 화면을 만들지 못했습니다(result.json 은 정상): {e}", flush=True)
    if FROZEN and not a.url:
        input("엔터를 누르면 닫힙니다.")


if __name__ == "__main__":
    main()
