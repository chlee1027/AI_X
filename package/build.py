r"""빌드 (10-19). 깨끗한 가상환경으로 돌린다: `.venv\Scripts\python build.py` (anaconda 기본 환경은 Jupyter·Qt 까지 묶여 2GB 가 되고 빌드가 실패했다).
코드(model, model2, package/detect.py)를 바꾼 뒤 이 파일 한 번이면 dist/AdDetector(API 없음)와 dist/AdDetector_API(API 판)가 다시 만들어진다.
모델만 바꿀 때는 빌드 없이 두 폴더의 model_v9n 폴더만 바꾼다."""
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--console", "--name", "AdDetector",
        "--paths", str(HERE.parent / "model2"), "--paths", str(HERE.parent / "model"),
        "--distpath", str(HERE / "dist"), "--workpath", str(HERE / "build"), "--specpath", str(HERE)]
for m in ("report_html", "llm_judge", "textfeat", "adlex", "adlex2", "train4", "admodel5", "admodel7", "train2", "rules4", "render4",
          "report", "site_scan", "common", "extra", "sklearn.ensemble._hist_gradient_boosting", "sklearn.linear_model",
          "sklearn.feature_extraction.text"):
    args += ["--hidden-import", m]
args += ["--collect-all", "playwright", str(HERE / "detect.py")]
subprocess.run(args, check=True)
base = HERE / "dist" / "AdDetector"
shutil.copytree(HERE / "model_v9n", base / "model_v9n", dirs_exist_ok=True)
shutil.copy2(HERE / "사용설명서.txt", base / "사용설명서.txt")
(base / "settings.json").write_text('{"api": false}\n', encoding="utf-8")
# 10-19: API 판 = 같은 폴더 사본 + settings.json {"api": true} (진행보고서 7-30절). 키는 넣지 않는다(사용자가 둔다)
# 10-20(7-50절): 모집요강 붙임3 에 따라 키는 실행 파일 옆 .env 의 ANTHROPIC_API_KEY 에서 읽는다. 두 폴더에 빈 .env.example 을 둔다.
# 사용자가 둔 .env(예전 api_key.txt 면 .env 로 옮김)는 다시 빌드해도 남긴다.
api = HERE / "dist" / "AdDetector_API"
env = (api / ".env").read_bytes() if (api / ".env").exists() else None
if env is None and (api / "api_key.txt").exists():
    env = b"ANTHROPIC_API_KEY=" + (api / "api_key.txt").read_bytes().strip() + b"\n"
(base / ".env.example").write_text("# Claude API 키를 아래 = 뒤에 넣고 파일 이름을 .env 로 바꾸세요(API 판에서만 씀)\nANTHROPIC_API_KEY=\n", encoding="utf-8")
if api.exists():
    shutil.rmtree(api)
shutil.copytree(base, api)
if env is not None:
    (api / ".env").write_bytes(env)
(api / "settings.json").write_text('{"api": true, "api_mode": "v2", "api_model": "claude-haiku-5-5", "api_wide": true}\n', encoding="utf-8")  # 10-21 v2(7-67절)
print("빌드 끝:", base / "AdDetector.exe", "(API 없음)")
print("빌드 끝:", api / "AdDetector.exe", "(API 판)")
