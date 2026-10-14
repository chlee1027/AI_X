"""trial 공용: 데이터 읽기, 페이지 주소·호스트, 카테고리 목록."""
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import yaml

# exe(PyInstaller)로 묶으면 함께 넣은 파일은 sys._MEIPASS 아래에 있다(C_data/lexicon/seed.yaml)
ROOT = Path(getattr(sys, "_MEIPASS", "")) if getattr(sys, "frozen", False) else Path(__file__).resolve().parents[1]
C = ROOT / "C_data"
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(parents=True, exist_ok=True)

# (카테고리 키, 파일, 양성 여부)
SOURCES = [
    ("HOMOGLYPH", "homoglyph/homoglyph_real_test_capped.yaml", True),
    ("JAMO", "jamo/jamo.yaml", True),
    ("TRANSPARENT", "transparent/transparent_real_test_rec20.yaml", True),
    ("OFFSCREEN", "offscreen/offscreen_originals.yaml", True),
    ("ETC", "etc/etc.yaml", True),
    ("COMBO", "combo/combo_real.yaml", True),
    ("DECOY", "decoy/decoy.yaml", False),
    ("TR_NEG", "transparent/transparent_real_negative.yaml", False),
]
MAIN4 = ("HOMOGLYPH", "JAMO", "TRANSPARENT", "OFFSCREEN")
URL_RE = re.compile(r"https?://[^\s)'\"<>]+")


def load_yaml(rel):
    return yaml.load((C / rel).read_text(encoding="utf-8"), Loader=yaml.CSafeLoader)


def page_url(it):
    o = it.get("origin")
    if isinstance(o, dict) and o.get("url"):
        return o["url"]
    m = URL_RE.search(str(it.get("source", "")))
    return m.group(0) if m else ""


def site_of(u):
    h = (urlparse(u).hostname or "").lower()
    for p in ("www.", "m.", "mobile."):
        if h.startswith(p):
            h = h[len(p):]
    return h


def load_all():
    """모든 샘플을 하나의 목록으로. 각 항목에 cat, positive 를 붙인다."""
    items = []
    for cat, rel, pos in SOURCES:
        for r in load_yaml(rel):
            r = dict(r)
            r["cat"] = cat
            r["positive"] = pos
            r["url"] = page_url(r)
            r["site"] = site_of(r["url"])
            items.append(r)
    return items


def gold_main4(it):
    """조각 하나의 요강 4종 정답 기법 목록(같은 expected_location)."""
    cat = it["cat"]
    if cat in MAIN4:
        codes = [cat]
        if cat == "TRANSPARENT" and "OFFSCREEN 별도" in str(it.get("notes") or ""):
            codes.append("OFFSCREEN")
        return codes
    if cat == "COMBO":
        codes = list(it.get("label_codes") or [])
        # trial 결정: 도메인 점 자리에 닮은 점 글자를 쓴 것은 HOMOGLYPH (사람 2 의 「점만 바꾼 도메인」 tier B 와 맞춤)
        if "HOMOGLYPH" not in codes and DOT_GLYPH_DOMAIN.search(str(it.get("evidence_text") or "")):
            codes.append("HOMOGLYPH")
        return codes
    return []


DOT_GLYPH_DOMAIN = re.compile(r"[A-Za-z0-9가-힣][｡。․．](?:com|net|kr|co|org|top|xyz|io|me|shop|site|vip|bet|win|cc|tv)(?![a-z])", re.I)
