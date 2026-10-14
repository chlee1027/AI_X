#!/usr/bin/env bash
# 블라인드 사이트 실행: 제출 기본값(25분 예산, 동시 6창)으로 돌리고, 넘길 묶음(zip)을 만든다.
# 받은 판을 고치기 전에 먼저 돌린다(고친 판으로 재면 블라인드가 아니다).
#   bash blind_run.sh <HTML 폴더> [시작 경로, 기본 /] [이름]   # 폴더를 127.0.0.1:8790 으로 띄워서 돌림(바깥 요청 차단)
#   bash blind_run.sh https://주소/ [이름]                      # 주소를 그대로 돌림
# 결과: out_blind/<이름>/ 와 out_blind/<이름>.zip (result.json, result_extra.json, run_log.json, version.txt, check.txt)
set -e
cd "$(dirname "$0")"
export PYTHONIOENCODING=utf-8
SRC="${1:?HTML 폴더나 주소를 주세요}"
PORT=8790
SRV=""
if [ -d "$SRC" ]; then
  ENTRY_PATH="${2:-/}"
  NAME="${3:-$(basename "$SRC")}"
  python -m http.server "$PORT" --bind 127.0.0.1 --directory "$SRC" > /dev/null 2>&1 &
  SRV=$!
  trap 'kill $SRV 2>/dev/null' EXIT
  for i in $(seq 30); do curl -s -o /dev/null "http://127.0.0.1:$PORT/" && break; sleep 1; done
  URL="http://127.0.0.1:$PORT${ENTRY_PATH}"
  EXT="--block-external"
else
  URL="$SRC"
  NAME="${2:-$(echo "$SRC" | sed -E 's#https?://##; s#/.*##')}"
  EXT=""
fi
OUT="out_blind/$NAME"
mkdir -p "$OUT"
echo "== $URL -> $OUT"
python run.py "$URL" --out "$OUT" $EXT > "$OUT/stdout.txt" 2>&1 || echo "run.py 종료 코드 $?"
python - "$OUT" <<'PY'
import hashlib, subprocess, sys
from datetime import datetime
from pathlib import Path
out = Path(sys.argv[1]); here = Path(".").resolve()
det = here.parent / "B_detector" if (here.parent / "B_detector").exists() else here.parent / "dev"
models = det / "models" if (det / "models").exists() else here / "models"
files = [here / "run.py", here / "page_probe.js", models / "models.pkl", models / "config.json"] + sorted(det.glob("*.py"))
try:
    rev = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=here).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", str(here.parent / "A_crawler"), str(here.parent / "B_detector")],
                           capture_output=True, text=True, cwd=here).stdout.strip()
except OSError:
    rev, dirty = "", ""
L = [f"실행 시각 {datetime.now().isoformat(timespec='seconds')}", f"저장소 커밋 {rev or '(저장소 밖)'}" + (" (커밋 안 한 변경 있음)" if dirty else "")]
L += [f"{hashlib.sha256(f.read_bytes()).hexdigest()[:16]}  {f.relative_to(here.parent)}" for f in files if f.exists()]
(out / "version.txt").write_text("\n".join(L) + "\n", encoding="utf-8")
PY
python check_result.py "$OUT" | tee "$OUT/check.txt" || true
python - "$OUT" <<'PY'
import sys, zipfile
from pathlib import Path
out = Path(sys.argv[1])
with zipfile.ZipFile(str(out) + ".zip", "w", zipfile.ZIP_DEFLATED) as z:
    for n in ("result.json", "result_extra.json", "run_log.json", "version.txt", "check.txt"):
        if (out / n).exists():
            z.write(out / n, n)
print("넘길 묶음:", str(out) + ".zip")
PY
