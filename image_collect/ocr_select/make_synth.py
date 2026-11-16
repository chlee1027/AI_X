"""OCR 엔진 고르기용 합성 배너 (재계획 3절 분리 규칙: OCR 엔진은 합성 이미지나 공개 샘플로 골라 11.9 전에 고정).

실제 수집 이미지는 한 장도 쓰지 않는다. 정답 글자를 알고 있는 배너를 만들어 엔진별 글자 오류율(CER)과 속도를 잰다.
정연의 학습용 합성기와는 다른 것이다(목적이 OCR 비교 하나뿐, 라벨 없음).

문구 출처: 1차 dev_data 의 evidence_text(실제 스팸 문구)에서 자른 조각 + 아래 일반 문구. 언어 비율은 한국어 위주에
인도네시아어·영어 섞음(수집 대상 페이지 구성을 따름).
변형: 배너 크기 4종, 글꼴 7종, 1~2줄, 배경(단색·그라디언트·잡음), 외곽선·그림자, 기울기 ±4도, JPEG 품질 35~90.
출력: ocr_select/synth/<id>.jpg, ocr_select/synth_gt.csv (id, text, lang, font, size, lines, quality)
"""
import csv
import glob
import os
import random
import re
import unicodedata

import yaml
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
DEV = os.path.join(HERE, "..", "..", "v2_20261017", "dev_data")
OUT = os.path.join(HERE, "synth")
N = 160
SEED = 20261104
F = "C:/Windows/Fonts/"
FONTS_KO = ["malgun.ttf", "malgunbd.ttf", "gulim.ttc", "batang.ttc", "HANDotumB.ttf", "HanSantteutDotum-Bold.ttf"]
FONTS_LATIN = FONTS_KO + ["impact.ttf", "arialbd.ttf"]
SIZES = [(728, 90), (468, 60), (300, 250), (320, 100)]
NORMAL_KO = ["2026 지역축제 참가자 모집", "도서관 휴관 안내 11월 10일", "신입생 입학설명회", "온라인 민원 신청 바로가기",
             "겨울철 화재 예방 수칙", "봉사활동 신청 기간 연장", "청년 일자리 박람회", "독감 예방접종 무료 실시",
             "개인정보 처리방침 개정 안내", "주민참여예산 제안 공모", "학술대회 논문 접수 마감", "가을 정기 세일 최대 50%",
             "동행복권 공식 판매점", "불법 도박 신고 1336", "스포츠토토 합법 구매처 안내", "대출 상담 은행 창구 방문"]
NORMAL_OTHER = [("Call for Papers Vol. 12 No. 3", "en"), ("Open Journal Systems", "en"), ("Penerimaan Mahasiswa Baru 2026", "id"),
                ("Seminar Nasional Pendidikan", "id"), ("Download Template Artikel", "id"), ("Free Shipping on Orders", "en")]


def lang_of(t):
    ko = len(re.findall(r"[가-힣]", t))
    lat = len(re.findall(r"[A-Za-z]", t))
    if ko and lat:
        return "mixed"
    return "ko" if ko else ("en" if lat else "none")


def spam_snippets(rng):
    out = []
    for f in glob.glob(os.path.join(DEV, "*", "*.yaml")):
        d = yaml.safe_load(open(f, encoding="utf-8"))
        items = d if isinstance(d, list) else next((v for v in d.values() if isinstance(v, list)), [])
        for it in items:
            if isinstance(it, dict) and it.get("is_positive") and it.get("evidence_text"):
                t = re.sub(r"[\u200b-\u200f\u00ad\ufeff]", "", str(it["evidence_text"]))
                t = re.sub(r"\s+", " ", t).strip()
                if 6 <= len(t):
                    out.append(t)
    rng.shuffle(out)
    snips = []
    for t in out:
        words = t.split(" ")
        if len(words) < 2:
            continue
        i = rng.randrange(0, max(1, len(words) - 3))
        s = " ".join(words[i:i + rng.randint(2, 5)])[:28].strip()
        # 글꼴에 없는 글자(이모지·특수 기호)는 정답이 애매해지므로 뺀다
        s = re.sub(r"[^A-Za-z0-9가-힣 .,:!%~+\-/@#]", "", unicodedata.normalize("NFKC", s))
        s = re.sub(r"\s+", " ", s).strip()
        if len(s) >= 4:
            snips.append(s)
    return snips


def gradient(size, c1, c2):
    w, h = size
    im = Image.new("RGB", size, c1)
    d = ImageDraw.Draw(im)
    for x in range(w):
        t = x / max(1, w - 1)
        d.line([(x, 0), (x, h)], fill=tuple(int(a + (b - a) * t) for a, b in zip(c1, c2)))
    return im


def make(rng, text, idx):
    size = rng.choice(SIZES)
    lang = lang_of(text)
    font_name = rng.choice(FONTS_KO if lang in ("ko", "mixed") else FONTS_LATIN)
    dark = rng.random() < 0.5
    c_bg = tuple(rng.randint(0, 70) for _ in range(3)) if dark else tuple(rng.randint(180, 255) for _ in range(3))
    c_fg = tuple(rng.randint(200, 255) for _ in range(3)) if dark else tuple(rng.randint(0, 60) for _ in range(3))
    kind = rng.choice(["solid", "grad", "noise"])
    if kind == "solid":
        im = Image.new("RGB", size, c_bg)
    elif kind == "grad":
        c2 = tuple(min(255, max(0, c + rng.randint(-60, 60))) for c in c_bg)
        im = gradient(size, c_bg, c2)
    else:
        im = Image.effect_noise(size, rng.randint(20, 60)).convert("RGB")
        im = Image.blend(Image.new("RGB", size, c_bg), im, 0.25)
    lines = [text]
    if size[1] >= 100 and len(text) > 12 and rng.random() < 0.5:
        sp = text.split(" ")
        k = max(1, len(sp) // 2)
        lines = [" ".join(sp[:k]), " ".join(sp[k:])]
        lines = [l for l in lines if l]
    w, h = size
    fs = int(h * (0.42 if len(lines) == 1 else 0.28))
    font = ImageFont.truetype(F + font_name, fs)
    while fs > 10 and max(font.getlength(l) for l in lines) > w * 0.92:
        fs -= 1
        font = ImageFont.truetype(F + font_name, fs)
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    total_h = len(lines) * fs * 1.2
    y = (h - total_h) / 2
    outline = rng.random() < 0.3
    shadow = rng.random() < 0.3
    for l in lines:
        x = (w - font.getlength(l)) / 2
        if shadow:
            d.text((x + 2, y + 2), l, font=font, fill=(0, 0, 0, 160))
        d.text((x, y), l, font=font, fill=c_fg + (255,), stroke_width=2 if outline else 0,
               stroke_fill=(255 - c_fg[0], 255 - c_fg[1], 255 - c_fg[2]) if outline else None)
        y += fs * 1.2
    if rng.random() < 0.3:
        layer = layer.rotate(rng.uniform(-4, 4), resample=Image.BICUBIC)
    im.paste(layer, (0, 0), layer)
    if rng.random() < 0.2:
        im = im.filter(ImageFilter.GaussianBlur(0.8))
    q = rng.randint(35, 90)
    fid = f"o{idx:03d}"
    im.save(os.path.join(OUT, fid + ".jpg"), quality=q)
    return dict(id=fid, text=" ".join(lines), lang=lang, font=font_name, size=f"{w}x{h}", lines=len(lines), quality=q)


def main():
    rng = random.Random(SEED)
    os.makedirs(OUT, exist_ok=True)
    spam = spam_snippets(rng)
    pool = [(s, "spam") for s in spam[: int(N * 0.6)]]
    pool += [(t, "normal") for t in NORMAL_KO] + [(t, "normal") for t, _ in NORMAL_OTHER]
    while len(pool) < N:
        pool.append((rng.choice(NORMAL_KO + [t for t, _ in NORMAL_OTHER]), "normal"))
    rng.shuffle(pool)
    rows = []
    for i, (t, src) in enumerate(pool[:N]):
        r = make(rng, t, i)
        r["source"] = src
        rows.append(r)
    with open(os.path.join(HERE, "synth_gt.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    print(len(rows), Counter(r["lang"] for r in rows), Counter(r["source"] for r in rows))


if __name__ == "__main__":
    main()
