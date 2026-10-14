#!/usr/bin/env bash
# 실제 공공 누리집 오탐 측정(사용자가 직접 실행). 광고가 없다고 보는 사이트라 출력은 원칙상 전부 오탐 후보.
# 단, 실제 게시판에 진짜 스팸 글이 있을 수 있으니 summarize_real.py 표를 사람이 보고 가른다.
# 부하를 줄이려고 사이트당 동시 2창, 100페이지, 10분 상한. 사이트는 순서대로 하나씩.
#   bash real_fp.sh                 # 아래 기본 목록
#   bash real_fp.sh https://a.go.kr/ https://b.go.kr/
cd "$(dirname "$0")"
SITES=("$@")
if [ ${#SITES[@]} -eq 0 ]; then
  # 1~6차에 쓴 26곳은 규칙 수정에 썼으므로 검증에 다시 쓰지 않는다(목록은 D_ui_docs 개발현황 문서)
  echo "사이트 주소를 인자로 주세요: bash real_fp.sh https://a.go.kr/ https://b.go.kr/ (1~6차 26곳 제외)"
  exit 1
fi
mkdir -p out_real
for u in "${SITES[@]}"; do
  h=$(echo "$u" | sed -E 's#https?://##; s#/.*##')
  echo "== $h"
  TOOL_SAVE_FEAT=1 python run.py "$u" --out "out_real/$h" --max-pages 100 --workers 2 --budget 600 > "out_real/$h.stdout.txt" 2>&1
  echo "   exit $?"
done
PYTHONIOENCODING=utf-8 python summarize_real.py
