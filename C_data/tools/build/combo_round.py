"""조합 덧붙이기 한 회차: 새로 받은 폴더 분석 -> 전체 후보 다시 만들기 -> 기존 200 에 「안 쏠리게」 덧붙이기.

1. 인자로 받은 회차 폴더(data/raw/etc/rNN)마다 analyze_obf 를 돌려 found_obf/rNN.json 을 만든다 (이미 있으면 건너뜀)
2. found_obf/r*.json 을 모두 합치고, 특징을 최신 규칙으로 다시 센다 (옛 결과에 없던 특징만 더함) -> obf_all.json
3. build_combo_real.py 로 후보(combo_cand.yaml)를 만들고 extend_combo.py 로 combo_ext.yaml 을 만든다

사용: python combo_round.py 목표개수 r31 r31p ...
"""
import json
import re
import subprocess
import sys
from pathlib import Path

C = Path(__file__).resolve().parents[2]
TOOLS, ETC = C / "tools", C / "data" / "raw" / "etc"
sys.path.insert(0, str(TOOLS / "analyze"))
import analyze_obf as A  # noqa: E402


def run(*args: str) -> str:
    return subprocess.run([sys.executable, *args], capture_output=True, text=True, encoding="utf-8").stdout


def main(target: str, rounds: list[str]) -> None:
    for r in rounds:
        out = ETC / "found_obf" / f"{r}.json"
        files = [str(f) for f in (ETC / r).glob("*_browser.html") if f.stat().st_size > 1000]
        if out.exists() or not files:
            print(r, "건너뜀" if out.exists() else "페이지 없음")
            continue
        lst = ETC / "found" / f"{r}.lst"
        lst.write_text("\n".join(files), encoding="utf-8")
        run(str(TOOLS / "analyze" / "analyze_obf.py"), str(out), "@" + str(lst))
        print(r, "페이지", len(files), "분석", out.exists())
    rows = []
    for f in sorted((ETC / "found_obf").glob("r*.json")):
        rows += json.loads(f.read_text(encoding="utf-8"))
    for x in rows:
        x["features"] = x["features"] + [k for k in A.features(x["text"]) if k not in x["features"]]
        # 폴더 이름이 바뀌어도(불법광고_수집 -> project/C_data) 원문을 찾도록 data\raw\etc 아래 상대 경로로 다시 붙인다
        rel = re.split(r"[\\/]data[\\/]raw[\\/]etc[\\/]", x["file"])[-1]
        x["file"] = str(ETC / rel)
    (ETC / "obf_all.json").write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(TOOLS / "build" / "build_combo_real.py"), str(ETC / "obf_all.json"), str(ETC / "combo_cand.yaml")],
                       capture_output=True, text=True, encoding="utf-8")
    # 선별이 실패하면 옛 후보 파일로 조용히 진행하지 않도록 멈춘다
    if r.returncode != 0:
        sys.exit("build_combo_real 실패:\n" + r.stderr[-1500:])
    print(r.stdout.splitlines()[0] if r.stdout else "")
    print(run(str(TOOLS / "build" / "extend_combo.py"), str(ETC / "combo_200_final.yaml"), str(ETC / "combo_cand.yaml"),
              str(ETC / "combo_ext.yaml"), target).strip())


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
