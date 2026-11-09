#!/usr/bin/env bash
# 수집 재개: collect/PAUSE 를 지우고 차례 드라이버를 다시 띄운다. 이미 돌고 있으면 띄우지 않는다.
# 정지: touch collect/PAUSE (진행 중인 페이지·이미지만 마치고 모든 프로세스가 끝난다. 기록은 지우지 않는다)
# 재개는 메인 대화의 지시가 있을 때만 실행한다.
cd "$(dirname "$0")/.." || exit 1
n=$(powershell.exe -NoProfile -Command "@(Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { \$_.CommandLine -match 'round_driver.py|tools.collect.py|tools.ocr_run.py' }).Count" | tr -d '\r')
if [ "${n:-0}" != "0" ]; then
  echo "아직 수집·OCR 프로세스 ${n}개가 돌고 있다. 끝난 뒤 다시 실행한다."
  exit 1
fi
rm -f collect/PAUSE logs/stop_request
PYTHONIOENCODING=utf-8 nohup .venv/Scripts/python -W ignore tools/round_driver.py >> logs/driver_stdout.log 2>&1 &
echo "재개함. 진행 기록: logs/driver.log"
