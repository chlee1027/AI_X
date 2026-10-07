"""실측 샘플을 카테고리별 6:2:2(학습·검증·테스트)로 나눈다. 묶음(캠페인) 단위로 나눠 같은 업자가 양쪽에 갈라지지 않게 한다.

묶음 만들기 (union-find)
  같은 묶음 = 다음 중 하나라도 같으면 이어 붙인다.
  - 같은 카테고리 안에서 출처 페이지의 호스트 (HOMOGLYPH 는 빼고 campaign 칸을 쓴다)
  - 광고 문구(evidence_text) 안의 연락 핸들(@abc123) · 도메인(blgm7.com, xn--…). 카테고리를 넘어 잇는다
    (조합·ETC·JAMO 에 같은 업자가 걸쳐 있다). 피해 사이트 자기 호스트와 흔한 정상 도메인은 뺀다
  - 사람 2 HOMOGLYPH 의 campaign 칸
  - 광고 문구가 글자까지 같은 것(공백 무시, 6자 이상), 같은 카테고리에서 한 문구가 다른 문구 안에 통째로 드는 것
나누기
  - 카테고리마다 목표 = 개수 x (0.6, 0.2, 0.2).
  - 한 묶음이 어느 카테고리의 20% 를 넘으면 학습에 고정한다(테스트가 그 업자 하나로 채워지지 않게).
  - 나머지 묶음은 큰 것부터, 카테고리·하위 유형별 목표와의 차이가 가장 적게 되는 쪽에 넣는다. 같은 크기는 SEED 로 섞는다.
  - HOMOGLYPH 는 권장판 370 으로 나누고, 전체판에만 있는 행은 같은 묶음이 간 쪽을 따른다. 묶음이 테스트면 그 행은 학습에 넣지 않는다.
  - OFFSCREEN 시험용(파생) 100 은 원문(같은 source·evidence)을 따른다.

2026-10-07 배정은 나누기 전 판(커밋 790b60d 의 data/)에서 돌린 것이다. 나눈 뒤 저장소에서 다시 돌리면 학습·검증만 놓고
다시 나누게 되니, 배정을 재현하려면 그 커밋을 꺼내 돌린다. 실제 배정은 data/splits/split_trainval.csv 가 정본이다.

사용: python tools/build/make_split.py            (표만 찍는다)
      python tools/build/make_split.py --out 파일   (배정 결과 JSON 저장)
"""
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data"
SEED = 20261007
RATIO = {"train": 0.6, "val": 0.2, "test": 0.2}
SPLITS = list(RATIO)
BIG = 0.2
URL_RE = re.compile(r"https?://[^\s)'\"<>]+")
HANDLE = re.compile(r"@([A-Za-z0-9_]{4,})")
DOMAIN = re.compile(r"\b((?:xn--)?[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)*\.(?:com|net|kr|io|me|org|xyz|co|shop|site|top|vip|info|"
                    r"club|bet|win|pro|cc|tv|biz|online|live|app|link|asia|store|fun|games?|casino|poker|world|today))\b")
COMMON = {"google.com", "naver.com", "daum.net", "kakao.com", "youtube.com", "w3.org", "schema.org", "facebook.com",
          "instagram.com", "twitter.com", "x.com", "t.me", "telegram.org", "bit.ly", "gmail.com", "naver.me",
          "jquery.com", "cloudflare.com", "googleapis.com", "gstatic.com", "imweb.me", "cafe24.com", "wordpress.org",
          "goo.gl", "tistory.com", "blog.naver.com", "archive.org", "web.archive.org", "github.com", "co.kr", "or.kr",
          "go.kr", "ac.kr", "ne.kr", "re.kr", "pe.kr"}


def load(p):
    return yaml.safe_load(Path(p).read_text(encoding="utf-8"))


def page_url(it):
    if isinstance(it.get("origin"), dict) and it["origin"].get("url"):
        return it["origin"]["url"]
    m = URL_RE.search(str(it.get("source", "")))
    return m.group(0) if m else ""


def host_of(u):
    h = (urlparse(u).hostname or "").lower()
    return h[4:] if h.startswith("www.") else h


def tokens(it, cat):
    h = host_of(page_url(it))
    toks = set()
    # 호스트는 같은 카테고리 안에서만 잇는다. 공공 게시판·검색 페이지 하나에 여러 업자가 섞여 있어
    # 카테고리를 넘어 이으면 서로 다른 업자가 한 묶음이 된다. HOMOGLYPH 는 사람 2 의 campaign 칸이 업자 단위라 호스트를 안 쓴다.
    if h and not cat.startswith("HOMOGLYPH"):
        toks.add(f"host:{cat}:{h}")
    text = str(it.get("evidence_text", ""))  # html 에는 피해 사이트 자기 링크가 섞여 광고 문구만 본다
    for m in HANDLE.finditer(text):
        toks.add("handle:" + m.group(1).lower())
    for m in DOMAIN.finditer(text.lower()):
        d = m.group(1)
        d = d[4:] if d.startswith("www.") else d
        if d in COMMON or d == h or h.endswith("." + d) or d.endswith("." + h) or len(d) < 6:
            continue
        toks.add("dom:" + d)
    if it.get("campaign"):
        toks.add("camp:" + str(it["campaign"]).lower())
    ev = re.sub(r"\s+", "", text)
    if len(ev) >= 6:  # 광고 문구가 글자까지 같으면 같은 업자로 본다(OFFSCREEN 은 여러 출처가 같은 문구를 쓴다)
        toks.add("ev:" + ev)
    return toks


class UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def gather():
    items = []  # (key, cat, sub, item, counted)
    for f, cat in (("samples/decoy.yaml", "DECOY"), ("samples/etc.yaml", "ETC"), ("samples/combo_real.yaml", "COMBO"),
                   ("samples/jamo.yaml", "JAMO"), ("offscreen/data/originals/offscreen_originals.yaml", "OFFSCREEN"),
                   ("homoglyph/homoglyph_real_test_capped.yaml", "HOMOGLYPH")):
        for it in load(D / f):
            # 조합의 subtype 은 수법 조합 문자열이라 거의 한두 개씩이다. 하위 유형으로 맞추면 모두 학습으로 쏠려 하나로 본다
            items.append((it["id"], cat, "combo" if cat == "COMBO" else it["subtype"], it, True))
    capped = {it["id"] for it in load(D / "homoglyph/homoglyph_real_test_capped.yaml")}
    for it in load(D / "homoglyph/homoglyph_real_test.yaml"):
        if it["id"] not in capped:
            items.append((it["id"], "HOMOGLYPH_FULL", it["subtype"], it, False))
    return items


def assign(items):
    uf = UF()
    for key, *_rest in items:
        uf.find("item:" + key)
    for key, cat, sub, it, _ in items:
        for t in tokens(it, cat):
            uf.union("item:" + key, t)
    # 한 문구가 다른 문구 안에 통째로 들면(「무료스포츠중계」 ⊂ 「무료스포츠중계사이트」) 같은 카테고리 안에서 잇는다
    evs = defaultdict(list)
    for key, cat, sub, it, _ in items:
        e = re.sub(r"\s+", "", str(it.get("evidence_text", "")))
        if len(e) >= 6:
            evs[cat.replace("_FULL", "")].append((e, key))
    for lst in evs.values():
        lst.sort(key=lambda x: len(x[0]))
        for i, (e, k) in enumerate(lst):
            for e2, k2 in lst[i + 1:]:
                if e in e2:
                    uf.union("item:" + k, "item:" + k2)
    group = {key: uf.find("item:" + key) for key, *_ in items}

    total = Counter(cat for _, cat, _, _, c in items if c)
    total_sub = Counter((cat, sub) for _, cat, sub, _, c in items if c)
    gcat = defaultdict(Counter)
    gsub = defaultdict(Counter)
    for key, cat, sub, _, c in items:
        if c:
            gcat[group[key]][cat] += 1
            gsub[group[key]][(cat, sub)] += 1

    cur = {s: Counter() for s in SPLITS}
    cur_sub = {s: Counter() for s in SPLITS}
    gsplit = {}
    forced = []
    for g, cc in gcat.items():
        if any(n > BIG * total[c] for c, n in cc.items()):
            gsplit[g] = "train"
            forced.append(g)
            cur["train"].update(cc)
            cur_sub["train"].update(gsub[g])

    rest = [g for g in gcat if g not in gsplit]
    rnd = random.Random(SEED)
    rnd.shuffle(rest)
    rest.sort(key=lambda g: -sum(gcat[g].values()))

    def cost(s, g):
        c = 0.0
        for cat, n in gcat[g].items():
            for t in SPLITS:
                after = cur[t][cat] + (n if t == s else 0)
                c += abs(after - RATIO[t] * total[cat]) / total[cat]
        for cs, n in gsub[g].items():
            if total_sub[cs] < 10:  # 아주 작은 하위 유형은 맞출 수 없어 빼고 카테고리 비율만 본다
                continue
            for t in SPLITS:
                after = cur_sub[t][cs] + (n if t == s else 0)
                c += 0.5 * abs(after - RATIO[t] * total_sub[cs]) / total_sub[cs]
        return c

    for g in rest:
        s = min(SPLITS, key=lambda s: (cost(s, g), SPLITS.index(s)))
        gsplit[g] = s
        cur[s].update(gcat[g])
        cur_sub[s].update(gsub[g])

    out = {}
    for key, cat, sub, it, counted in items:
        g = group[key]
        s = gsplit.get(g, "train")  # 전체판에만 있는 묶음은 학습
        if not counted and s == "test":
            s = "test_campaign_extra"  # 테스트 묶음의 전체판 덧 행: 학습에 넣지 않는다
        elif not counted and s == "val":
            s = "val_campaign_extra"
        out[key] = {"category": cat, "subtype": sub, "split": s, "group": g}
    return out, forced, gcat


def report(out, forced, gcat):
    rows = defaultdict(Counter)
    for v in out.values():
        rows[v["category"]][v["split"]] += 1
    lines = ["카테고리 | 학습 | 검증 | 테스트 | 합계 | 비율"]
    for cat in ("DECOY", "ETC", "COMBO", "JAMO", "OFFSCREEN", "HOMOGLYPH", "HOMOGLYPH_FULL"):
        r = rows[cat]
        n = sum(r.values())
        if cat == "HOMOGLYPH_FULL":
            lines.append(f"{cat}(전체판에만 있는 행) | {r['train']} | {r['val_campaign_extra']} | 테스트 묶음이라 뺌 {r['test_campaign_extra']} | {n} |")
            continue
        lines.append(f"{cat} | {r['train']} | {r['val']} | {r['test']} | {n} | "
                     f"{r['train'] / n:.2f}:{r['val'] / n:.2f}:{r['test'] / n:.2f}")
    sub = defaultdict(Counter)
    for v in out.values():
        if v["category"] != "HOMOGLYPH_FULL":
            sub[(v["category"], v["subtype"])][v["split"]] += 1
    lines.append("")
    lines.append("하위 유형 | 학습 | 검증 | 테스트")
    for (c, s), r in sorted(sub.items()):
        lines.append(f"{c}:{s} | {r['train']} | {r['val']} | {r['test']}")
    lines.append("")
    lines.append(f"묶음 수 {len(gcat)}, 학습 고정(한 카테고리 20% 초과) {len(forced)}")
    for g in forced:
        lines.append(f"  고정 {g[:60]} {dict(gcat[g])}")
    big = sorted(gcat, key=lambda g: -sum(gcat[g].values()))[:12]
    lines.append("큰 묶음 12:")
    for g in big:
        sp = next(v["split"] for v in out.values() if v["group"] == g)
        lines.append(f"  {sp:5} {sum(gcat[g].values()):4} {g[:60]} {dict(gcat[g])}")
    return "\n".join(lines)


def main(argv):
    out, forced, gcat = assign(gather())
    rep = report(out, forced, gcat)
    if "--out" in argv:
        p = Path(argv[argv.index("--out") + 1])
        p.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
        p.with_suffix(".txt").write_text(rep + "\n", encoding="utf-8")
    else:
        sys.stdout.reconfigure(errors="replace")
        print(rep)


if __name__ == "__main__":
    main(sys.argv[1:])
