"""공용: 데이터 읽기, 정답(요강 4종) 만들기, 경로.

표본 1건 = html 발췌 + css. 정답 = (발췌 안 위치 선택자, 기법) 묶음. 기법은 요강 4종만 다룬다.
  - HOMOGLYPH · JAMO · TRANSPARENT · OFFSCREEN 카테고리: 같은 폴더 정답 json 에 그 id 의 4종 정답이 있으면 그것,
    없으면 (expected_location, 카테고리).
  - COMBO: combo/answer_result.json 의 4종 정답(없으면 4종 정답 0건).
  - ETC · DECOY · 음성: 4종 정답 0건(4종 기준으로는 음성).
읽기 경로는 인자로 받는다. 개발은 v2_20261017/dev_data 만 쓴다.
"""
import json
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
DEV = HERE.parent / "dev_data"
CACHE = HERE / "cache"
MAIN4 = ("HOMOGLYPH", "JAMO", "TRANSPARENT", "OFFSCREEN")

# (카테고리, 양성 여부, yaml, 4종 정답 json)
SOURCES = [
    ("HOMOGLYPH", True, "homoglyph/homoglyph_real_test_capped.yaml", None),
    ("JAMO", True, "jamo/jamo.yaml", None),
    ("TRANSPARENT", True, "transparent/transparent_real_test_rec20.yaml", "transparent/answer_result.json"),
    ("OFFSCREEN", True, "offscreen/offscreen_originals.yaml", None),
    ("OFFSCREEN", True, "offscreen/offscreen_real_test_rec.yaml", "offscreen/answer_result_real.json"),
    ("ETC", True, "etc/etc.yaml", None),
    ("COMBO", True, "combo/combo_real.yaml", "combo/answer_result.json"),
    ("DECOY", False, "decoy/decoy.yaml", None),
    ("TR_NEG", False, "transparent/transparent_real_negative.yaml", None),
    ("OF_NEG", False, "offscreen/offscreen_real_negative.yaml", None),
]


def _answers(path):
    """정답 json -> {표본 id: [(위치, 기법)]} (요강 4종, 위반 항목만)."""
    if not path.exists():
        return {}
    d = json.loads(path.read_text(encoding="utf-8"))
    out = {}
    for f in d.get("findings") or []:
        tech = f.get("technique")
        if tech not in MAIN4 or str(f.get("is_violation")) not in ("True", "true", "1"):
            continue
        fid = str(f["id"])
        base = fid.rsplit("_", 1)[0] if fid.endswith("_" + tech) else fid
        out.setdefault(base, []).append((f["location"], tech))
    return out


def load_samples(root):
    """root 아래 데이터 -> 표본 목록. 각 표본: id, cat, html, css, gold[(위치, 기법)]."""
    root = Path(root)
    items = []
    for cat, pos, rel, ans in SOURCES:
        p = root / rel
        if not p.exists():
            continue
        rows = yaml.load(p.read_text(encoding="utf-8"), Loader=yaml.CSafeLoader) or []
        amap = _answers(root / ans) if ans else {}
        for r in rows:
            sid = str(r["id"])
            if cat in MAIN4:
                gold = amap.get(sid) or [(str(r.get("expected_location") or ""), cat)]
            elif cat == "COMBO":
                gold = amap.get(sid, [])
            else:
                gold = []
            items.append({"id": sid, "cat": cat, "subtype": str(r.get("subtype") or ""),
                          "html": str(r.get("html") or ""), "css": str(r.get("css") or ""),
                          "gold": sorted(set((loc, t) for loc, t in gold if loc))})
    return items
