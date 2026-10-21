"""한 줄 채점 (10-19). 검사 -> 결과 보관 -> 채점을 한 번에 한다. 사용자가 직접 돌린다. 출력은 score_key.py 와 같은 집계뿐이다.

근거: 지금까지 검사(exe 또는 scan4) -> 결과 복사 -> score_key 를 따로 쳐야 해서 경로 실수가 잦았다(진행보고서 9절).
  - 기본은 실제 제출물(package/dist/AdDetector/AdDetector.exe)로 검사한다. --run runs/v6 처럼 주면 scan4 로 그 모델을 쓴다.
  - 결과는 scans/<이름>/ 에 보관하고(result.json·debug.json·report.html), 점수는 scans/<이름>/score.txt 에도 남긴다.
  - 결과 화면은 자동으로 열지 않는다(채점 대상 사이트 내용을 열어 보지 않도록).

사용: python 채점.py <사이트 주소> <정답 파일> [이름] [--run runs/v6]
  예: python 채점.py http://127.0.0.1:8771/ "C:\\Users\\채현\\Documents\\...\\truth.json" holdout2
  이름을 빼면 날짜·시각으로 만든다. 정답 파일은 탐색기에서 끌어다 놓아도 된다.
"""
import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXE = HERE.parent / "package" / "dist" / "AdDetector" / "AdDetector.exe"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("answer")
    ap.add_argument("name", nargs="?")
    ap.add_argument("--run", help="exe 대신 scan4 로 이 모델 폴더를 쓴다(예: runs/v6)")
    ap.add_argument("--api", action="store_true", help="API 판(dist/AdDetector_API)으로 검사")
    ap.add_argument("--max-pages", type=int, default=2000)  # 10-21 실행 파일과 같게(7-68절)
    ap.add_argument("--report", default="block", help="--run 일 때 보고 방식(inner·block 등, 7-47절)")
    ap.add_argument("--extra", nargs="*", default=[], help="--run 일 때 같은 크롤로 함께 채점할 보고 방식(예: --report block --extra inner)")
    ap.add_argument("--scan-api", action="store_true", help="--run 일 때 scan4 에 API 판정(demote)을 켠다")
    a = ap.parse_args()
    answer = Path(a.answer.strip('"'))
    if not answer.exists():
        sys.exit(f"정답 파일이 없습니다: {answer}")
    tag = Path(a.run).name if a.run else ("exe-api" if a.api else "exe")
    name = a.name or datetime.now().strftime("%m%d_%H%M")
    out = HERE / "scans" / f"{tag}_{name}"
    if out.exists() and any(out.iterdir()):
        sys.exit(f"이미 있는 이름입니다(덮어쓰지 않음): {out}  다른 이름을 주세요.")
    out.mkdir(parents=True, exist_ok=True)
    print(f"[1/2] 검사: {a.url}  ({'exe' if not a.run else a.run}) -> {out}", flush=True)
    if a.run:
        cmd = [sys.executable, str(HERE / "scan4.py"), "--url", a.url, "--run", a.run, "--out", str(out), "--max-pages", str(a.max_pages),
               "--minutes", "20", "--delay", "0.2", "--report", a.report] + (["--extra", *a.extra] if a.extra else []) + (["--api"] if a.scan_api else [])
    else:
        exe = EXE.parent.parent / "AdDetector_API" / "AdDetector.exe" if a.api else EXE
        if not exe.exists():
            sys.exit(f"exe 가 없습니다: {EXE}  (package 폴더에서 .venv\\Scripts\\python build.py)")
        cmd = [str(exe), a.url, "--out", str(out), "--no-open", "--max-pages", str(a.max_pages)]
    r = subprocess.run(cmd)
    if r.returncode != 0 or not (out / "result.json").exists():
        sys.exit("검사가 실패했습니다. 위 오류 문구를 확인하세요.")
    print("[2/2] 채점", flush=True)
    log = f"site: {a.url}\nmodel: {tag}\n"
    for m_, rf in [(a.report if a.run else "exe", "result.json")] + ([(x, f"result_{x}.json") for x in a.extra] if a.run else []):
        r = subprocess.run([sys.executable, str(HERE / "score_key.py"), str(out / rf), str(answer)],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        print(f"--- 보고 방식 {m_} ---\n" + r.stdout, end="")
        if r.returncode != 0:
            print(r.stderr, end="")
            sys.exit("채점이 실패했습니다.")
        log += f"\n--- 보고 방식 {m_} ---\n{r.stdout}"
    (out / "score.txt").write_text(log, encoding="utf-8")
    print(f"점수 기록: {out / 'score.txt'}")


if __name__ == "__main__":
    main()
