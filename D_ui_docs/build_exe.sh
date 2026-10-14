#!/usr/bin/env bash
# 탐지 도구 exe 묶기(PyInstaller onedir, UPX 안 씀). 브라우저는 묶지 않고 Windows 기본 Edge(channel="msedge")를 쓴다.
# anaconda 로 묶으면 1.5GB 가 되므로 필요한 패키지만 든 가상환경에서 묶는다(290MB).
# 판은 models.pkl 을 만든 판과 맞춘다(scikit-learn 1.5.1 피클).
#   bash D_ui_docs/build_exe.sh <작업 폴더>   (작업 폴더는 저장소 밖에 둔다)     # 결과: <작업 폴더>/dist/detect_tool/detect_tool.exe
set -e
cd "$(dirname "$0")"
W="${1:?작업 폴더를 주세요}"
T=$(pwd -W)
if [ ! -x "$W/venv/Scripts/python.exe" ]; then
  python -m venv "$W/venv"
  "$W/venv/Scripts/python.exe" -m pip install -q scikit-learn==1.5.1 scipy==1.13.1 numpy==1.26.4 pyyaml==6.0.1 playwright==1.63.0 pyinstaller
fi
"$W/venv/Scripts/python.exe" -m PyInstaller "$T/../A_crawler/run.py" --onedir --noupx --noconfirm --name detect_tool --paths "$T/../B_detector" \
  --add-data "$T/../A_crawler/page_probe.js;." --add-data "$T/../B_detector/models;models" --add-data "$T/../C_data/lexicon/seed.yaml;C_data/lexicon" \
  --distpath "$W/dist" --workpath "$W/build" --specpath "$W"
echo "$W/dist/detect_tool/detect_tool.exe"
