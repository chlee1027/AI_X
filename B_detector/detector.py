"""요강 4종 탐지기: 계산 스타일 기법 신호(숨김·글자 위장) x 내용 판정(문자 n-gram 로지스틱 회귀 + 어휘·연락처 특징).

A_crawler/run.py 가 페이지마다 Detector.detect 를 부른다. 학습한 모델은 B_detector/models/models.pkl,
규칙 문턱은 B_detector/models/config.json. 학습·평가 스크립트는 평가 데이터가 섞이지 않게 사람 1(C)의 평가 환경에 둔다.
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict

import numpy as np
import yaml
from scipy.sparse import hstack, csr_matrix
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

from common import C, MAIN4, OUT, gold_main4, load_all, site_of
from textnorm import hg_signal, jamo_signal, normalize

sys.stdout.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------- 내용 특징

LEX = yaml.load((C / "lexicon/seed.yaml").read_text(encoding="utf-8"), Loader=yaml.CSafeLoader)
LEX_N = {}
for r in LEX:
    LEX_N.setdefault(r["category"], []).append(normalize(r["term"], keep_space=False))
HANDLE_RE = re.compile(r"(텔레|텔|카톡|카톡|톡|라인|line|tele|kakao|문의|연락)\W{0,3}[@:]?\W{0,2}[a-z0-9_]{3,}", re.I)
AT_RE = re.compile(r"@\s?[a-z0-9_]{3,}", re.I)
DOM_RE = re.compile(r"[a-z0-9-]{2,}\s?\.\s?(com|net|kr|top|xyz|io|me|org|co|shop|site|vip|bet|win|cc|tv|online|live|app|link)\b", re.I)
LETTER_RE = re.compile(r"[가-힣ㄱ-ㅎㅏ-ㅣA-Za-z]")
PHONE_RE = re.compile(r"0\d{1,2}\W{0,3}\d{3,4}\W{0,3}\d{4}")


def feats(norm_text):
    t = norm_text.replace(" ", "")
    f = [sum(1 for w in LEX_N.get(c, []) if w and w in t) for c in ("gambling_core", "gambling_lure", "contact", "adult", "whitelist")]
    f += [len(HANDLE_RE.findall(norm_text)), len(AT_RE.findall(norm_text)), len(DOM_RE.findall(norm_text)),
          len(PHONE_RE.findall(norm_text)), min(len(t), 500) / 500]
    return f


class Content:
    def __init__(self):
        self.vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(1, 3), min_df=2, sublinear_tf=True, max_features=60000)
        self.clf = LogisticRegression(max_iter=2000, C=4.0, class_weight="balanced")

    def _x(self, texts, fit=False):
        n = [normalize(t) for t in texts]
        a = self.vec.fit_transform(n) if fit else self.vec.transform(n)
        b = csr_matrix(np.log1p(np.array([feats(x) for x in n], dtype=float)))
        return hstack([a, b]).tocsr()

    def fit(self, texts, y):
        self.clf.fit(self._x(texts, fit=True), y)
        return self

    def proba(self, texts):
        if not texts:
            return np.array([])
        return self.clf.predict_proba(self._x(texts))[:, 1]


def train_texts(items, feat):
    """양성: 광고 문구(evidence_text). 음성: 음성 조각의 모든 글자 요소 + evidence."""
    X, y = [], []
    for it in items:
        if it["positive"]:
            if str(it.get("evidence_text") or "").strip():
                X.append(it["evidence_text"]); y.append(1)
        else:
            seen = set()
            for e in feat[it["id"]]["els"]:
                for t in (e["own"].strip(), e["text"].strip()):
                    if 2 <= len(t) <= 600 and t not in seen:
                        seen.add(t); X.append(t); y.append(0)
            if it.get("evidence_text"):
                X.append(it["evidence_text"]); y.append(0)
    return X, y


# ---------------------------------------------------------------- 기법 신호(계산 스타일)

def lum(c):
    def ch(v):
        v = v / 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def contrast(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def px(v):
    try:
        return float(str(v).replace("px", ""))
    except ValueError:
        return 0.0


def hidden_tr(e):
    if e["disp_none"]:
        return False
    col = e["color"] or [0, 0, 0, 1]
    if e["cum_op"] <= 0.05:
        return True
    if col[3] <= 0.05:
        return True
    if "rgba(0, 0, 0, 0)" in e["tfill"] or e["tfill"] == "transparent":
        if "text" not in e["bgclip"]:
            return True
    if not e["bg_img"] and contrast(col, e["eff_bg"]) < 1.15:
        return True
    return False


def hidden_of(e):
    if e["disp_none"] or e["visibility"] == "hidden":
        return True
    if e["font_size"] <= 1.0:
        return True
    if e["w"] > 0 or e["h"] > 0:
        if e["x"] + e["w"] <= 0 or e["y"] + e["h"] <= 0 or e["x"] >= 2000:
            return True
    if e["text_indent"] <= -500:
        return True
    clip = (e["clip"] or "").replace(" ", "")
    m = re.match(r"rect\(([^,]+),([^,]+),([^,]+),([^,]+)\)", clip)
    if m and e["position"] in ("absolute", "fixed"):
        t, r, b, l = (px(v) if v != "auto" else None for v in m.groups())
        if (t is not None and t >= max(e["h"], 1)) or (l is not None and l >= max(e["w"], 1)) or            (t is not None and b is not None and b <= t + 1) or (l is not None and r is not None and r <= l + 1):
            return True
    cp = e["clip_path"] or ""
    if "inset(50%" in cp or "circle(0" in cp or "inset(100%" in cp:
        return True
    if (e["w"] <= 1 or e["h"] <= 1) and e["overflow"] == "hidden" and e["text"].strip():
        return True
    return False


# 화면에 그리는 글자가 아닌 요소(스크립트·JSON-LD·스타일). 기본이 display:none 이라 숨김 영역으로 잡혔다(사람 3 원본 OF-050)
NON_TEXT = {"script", "style", "noscript", "template"}


SOCIAL = {"facebook.com", "twitter.com", "x.com", "instagram.com", "youtube.com", "linkedin.com", "google.com", "whatsapp.com",
          "wa.me", "t.me", "pinterest.com", "tiktok.com", "naver.com", "kakao.com", "blog.naver.com", "play.google.com",
          "apps.apple.com", "wordpress.org", "w3.org"}


def is_ext(href, site):
    from common import site_of
    if not href.startswith("http"):
        return False
    h = site_of(href)
    # site_of 가 www. 를 떼므로 정부24(www.gov.kr)는 「gov.kr」 로 온다. 앞에 점이 없어도 맞게 (^|\.) 로 건다.
    # 외국 정부 도메인(일본 지자체 lg.jp·중앙 go.jp, 중남미 gob.xx, 프랑스어권 gouv.xx)은 실측 6차 인천시 자매도시 표에서 나왔다
    if re.search(r"(^|\.)((go|ac|re|mil|or)\.kr|(gov|edu|mil)(\.[a-z]{2})?|go\.id|ac\.id|(go|lg)\.jp|gob\.[a-z]{2}|gouv\.[a-z]{2})$", h or ""):
        return False  # 공공·교육 기관끼리의 링크(관련 사이트·바로가기)는 숨겨 있어도 흔하다(DECOY hidden_menu)
    # SNS 는 하위 도메인까지(pf.kakao.com, story.kakao.com: 실제 누리집 숨김 SNS 메뉴)
    social = any(h == d or h.endswith("." + d) for d in SOCIAL)
    return bool(h) and h != site and not site.endswith("." + h) and not h.endswith("." + site) and not social


# ---------------------------------------------------------------- 탐지

class Detector:
    def __init__(self, content, th, mode="ad_elem", jamo_guard=True, dedupe=True):
        self.c = content
        self.th = th  # {"hide": p, "text": p}
        self.mode = mode
        self.jamo_guard = jamo_guard
        self.dedupe = dedupe

    def detect(self, fr, site=""):
        els = fr["els"]
        if not els:
            return []
        par = {e["i"]: e["parent"] for e in els}
        kids = defaultdict(list)
        for e in els:
            kids[e["parent"]].append(e["i"])
        by = {e["i"]: e for e in els}

        def subtree(i):
            st, out = [i], []
            while st:
                j = st.pop(); out.append(j); st.extend(kids.get(j, []))
            return out

        out = set()
        # 숨김 유형: 숨김 시작 요소마다, 그 안에서 광고 글자를 직접 가진 요소를 고른다
        own_txt = {e["i"]: e["own"].strip() for e in els}
        regions = []
        for tech, fn in (("TRANSPARENT", hidden_tr), ("OFFSCREEN", hidden_of)):
            flag = {e["i"]: fn(e) for e in els}
            for e in els:
                if flag[e["i"]] and e["text"].strip() and not flag.get(par[e["i"]], False) and e["tag"] not in NON_TEXT:
                    regions.append((tech, e["i"]))
        if regions:
            texts, keys = [], []
            for tech, r in regions:
                keys.append((tech, r, r)); texts.append(by[r]["text"])
                for j in subtree(r):
                    if len(own_txt[j]) >= 2 and by[j]["tag"] not in NON_TEXT:
                        keys.append((tech, r, j)); texts.append(own_txt[j] + (" " + by[j]["href"] if is_ext(by[j]["href"], site) else ""))
            pr = self.c.proba(texts)
            # 숨긴 외부 링크는 주소를 붙여 판정하는데, 주소만 붙어도 점수가 크게 오른다(실제 누리집 패밀리 사이트 메뉴).
            # 그래서 링크 글자만으로도 ext_own 이상이어야 광고로 본다
            # 숨김 영역의 뿌리 자체가 링크인 경우는 뺀다. 넣으면 실제 누리집 「일정 더보기」류는 막지만 교차검증 TRANSPARENT 맞힘 10건을 잃는다(68.7 -> 68.0)
            # 다만 text-indent 로 글자만 밀어낸 링크(아이콘 버튼의 접근성 글자, 실제 누리집 「중구청」)는 뿌리여도 넣는다
            ti_root = lambda tech, r, j: j == r and tech == "OFFSCREEN" and self.th.get("ext_own_ti") and by[r]["text_indent"] <= -500
            ext_k = [n for n, (tech, r, j) in enumerate(keys) if (j != r or ti_root(tech, r, j)) and by[j]["tag"] == "a" and is_ext(by[j]["href"], site)]
            own_p = dict(zip(ext_k, self.c.proba([own_txt[keys[n][2]] for n in ext_k]))) if ext_k and self.th.get("ext_own", 0) > 0 else {}
            # 링크 목록 메뉴: 숨김 영역 안 링크가 이 사이트 밖의 서로 다른 호스트 menu_hosts 곳 이상을 가리키면 관련 사이트·SNS 메뉴로 본다
            # (실제 누리집 1~3차 오탐의 대부분). 그 안의 외부 링크는 주소를 붙이지 않고 링크 글자만으로, 일반 숨김 문턱으로 판정한다.
            # 숨긴 스팸 링크 묶음도 호스트가 여럿이지만 앵커 글자 자체가 광고라 글자만으로 걸린다
            menu = set()
            K = self.th.get("menu_hosts", 0)
            if K:
                def ext_hosts(r):
                    hs = {site_of(by[j]["href"]) for j in subtree(r) if by[j]["tag"] == "a" and by[j]["href"].startswith("http")}
                    return {h for h in hs if h and h != site and not h.endswith("." + site) and not site.endswith("." + h)}
                # 슬라이더는 칸마다 따로 화면 밖에 있어 칸 하나가 숨김 영역 하나가 된다. 같은 부모 아래 숨김 영역들은 합쳐서 센다
                sib = defaultdict(list)
                for tech, r in regions:
                    sib[(tech, par[r] if self.th.get("menu_sib") else r)].append(r)
                for (tech, _), rs in sib.items():
                    if len(set().union(*(ext_hosts(r) for r in rs))) >= K:
                        menu.update((tech, r) for r in rs)
            # 펼침 메뉴: 부모가 보이는 li 인 display:none 영역은 마우스를 올리면 펴지는 하위 메뉴다(실측 6차 경찰청 영문판 「Korea Today」).
            # 학습 데이터에서 이 꼴의 양성은 0건, 음성(DECOY) 13건. 링크 목록 메뉴와 같이 외부 링크를 글자만으로 일반 숨김 문턱에 댄다
            if self.th.get("menu_li"):
                menu.update((tech, r) for tech, r in regions if tech == "OFFSCREEN" and by[r]["disp_none"]
                            and par[r] in by and by[par[r]]["tag"] == "li" and not by[par[r]]["disp_none"])
            if menu:
                mk = [n for n, (tech, r, j) in enumerate(keys) if (tech, r) in menu and j != r and n not in own_p
                      and by[j]["tag"] == "a" and is_ext(by[j]["href"], site)]
                own_p.update(zip(mk, self.c.proba([own_txt[keys[n][2]] for n in mk])) if mk else [])
            reg_p = {}
            ads = defaultdict(list)
            for n, ((tech, r, j), p) in enumerate(zip(keys, pr)):
                if j == r and (tech, r) not in reg_p:
                    reg_p[(tech, r)] = p
                # OFFSCREEN 만 따로 문턱(hide_of)을 둘 수 있다. 없으면 hide
                thr = (self.th.get("hide_ext", self.th["hide"]) if (by[j]["tag"] == "a" and is_ext(by[j]["href"], site))
                       else self.th.get("hide_of", self.th["hide"]) if tech == "OFFSCREEN" else self.th["hide"])
                if (tech, r) in menu and j != r and n in own_p:
                    p, thr = own_p[n], self.th["hide"]
                elif n in own_p and own_p[n] < self.th.get("ext_own", 0):
                    continue
                # 숫자·기호뿐인 글자(연혁의 「1988」, 표의 「188」)는 광고 문구가 될 수 없다
                if self.th.get("need_letter") and not LETTER_RE.search(own_txt[j]):
                    continue
                if p >= thr and len(own_txt[j]) >= 2:
                    ads[(tech, r)].append(j)
            best = {}
            for (tech, r, j), p in zip(keys, pr):
                if j != r or len(own_txt[j]) >= 2:
                    if len(own_txt[j]) >= 2 and ((tech, r) not in best or p > best[(tech, r)][1]):
                        best[(tech, r)] = (j, p)
            for (tech, r), p in reg_p.items():
                a = sorted(set(ads[(tech, r)]))
                if self.mode == "region":
                    if p >= self.th["hide"]:
                        out.add((r, tech))
                elif a:
                    for j in a:
                        out.add((j, tech))
                elif p >= self.th["hide"] and self.th.get("fallback", True):
                    # 영역 전체만 광고 점수가 높고 요소 하나하나는 낮을 때 가장 높은 요소를 낸다.
                    # 실제 누리집의 접힌 운영원칙(도박·음란 게시물 삭제 안내)이 여기에 걸린다
                    out.add((best[(tech, r)][0] if (tech, r) in best else r, tech))
        # 글자 유형
        cands = []
        for e in els:
            own = own_txt[e["i"]]
            if not own:
                continue
            hg = hg_signal(own)
            jm = jamo_signal(own)
            if hg:
                cands.append((e["i"], "HOMOGLYPH", e["text"]))
            if jm and (not hg or not self.jamo_guard or set(jm) & {"decomposed", "conjoining"}):
                cands.append((e["i"], "JAMO", e["text"]))
        if cands:
            for (i, tech, _), p in zip(cands, self.c.proba([c[2] for c in cands])):
                if p >= self.th["text"]:
                    out.add((i, tech))
        if self.dedupe:
            anc = {}
            for i, _ in out:
                a, j = set(), i
                while j in par and par[j] != -1:
                    j = par[j]; a.add(j)
                anc[i] = a
            # 같은 기법이 조상과 자손에 함께 나오면 자손(글자를 직접 가진 쪽)을 남긴다
            out = {(i, t) for i, t in out if not any(t2 == t and i in anc[j] for j, t2 in out if j != i)}
        return sorted(out)


# ---------------------------------------------------------------- 평가

def ancestors(els, i):
    par = {e["i"]: e["parent"] for e in els}
    s = set()
    while i in par and par[i] != -1:
        i = par[i]; s.add(i)
    return s


def pages(items):
    """같은 url · html · css 조각은 한 페이지로 본다(링크마다 샘플이 따로 있는 경우). 첫 조각의 렌더링을 쓴다."""
    pg = defaultdict(list)
    for it in items:
        pg[(it["url"], it.get("html"), it.get("css"))].append(it)
    return list(pg.values())


def evaluate(items, feat, preds):
    """preds: 페이지 대표 id -> [(idx, tech)]. 반환: 카테고리별·기법별 표."""
    by_cat = defaultdict(Counter)
    by_tech = defaultdict(Counter)
    errors = []
    for grp in pages(items):
        it = grp[0]
        fr = feat[it["id"]]
        P = set(preds.get(it["id"], []))
        G = set()
        for x in grp:
            if x["positive"]:
                G |= {(feat[x["id"]]["exp_idx"], code) for code in gold_main4(x)}
        cat = it["cat"]
        for g in G:
            hit = g in P
            near = hit or any(t == g[1] and (i in ancestors(fr["els"], g[0]) or g[0] in ancestors(fr["els"], i)) for i, t in P)
            by_cat[cat]["gold"] += 1; by_cat[cat]["tp"] += hit; by_cat[cat]["near"] += near
            by_tech[g[1]]["gold"] += 1; by_tech[g[1]]["tp"] += hit
            if not hit:
                errors.append(("FN", it["id"], cat, g[1], near))
        for p in P - G:
            by_cat[cat]["fp"] += 1; by_tech[p[1]]["fp"] += 1
            errors.append(("FP", it["id"], cat, p[1], False))
        by_cat[cat]["frag"] += 1
        if not it["positive"] and P:
            by_cat[cat]["frag_fp"] += 1
    return by_cat, by_tech, errors


def report(name, by_cat, by_tech, note):
    L = [f"# {name}", "", note, "", "## 카테고리별 (페이지 단위: 같은 url·html·css 조각을 합침)", "",
         "| 카테고리 | 페이지 | 정답 건 | 맞힘 | 재현율 | 위치만 어긋남 포함 | 오답 출력 | 오탐 페이지 |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for c, v in by_cat.items():
        g = v["gold"]
        rec = f"{v['tp'] / g:.1%}" if g else "-"
        near = f"{v['near'] / g:.1%}" if g else "-"
        ffp = f"{v['frag_fp']} ({v['frag_fp'] / v['frag']:.1%})" if g == 0 else "-"
        L.append(f"| {c} | {v['frag']} | {g} | {v['tp']} | {rec} | {near} | {v['fp']} | {ffp} |")
    L += ["", "## 요강 4종별 (요강식: 재현율 = 맞힘/정답, 정밀도 = 맞힘/전체 출력)", "",
          "| 기법 | 정답 건 | 맞힘 | 오답 출력 | 재현율 | 정밀도 | F1 |", "|---|---:|---:|---:|---:|---:|---:|"]
    TG = TP = FP = 0
    for t in MAIN4:
        v = by_tech[t]
        g, tp, fp = v["gold"], v["tp"], v["fp"]
        TG += g; TP += tp; FP += fp
        r = tp / g if g else 0; p = tp / (tp + fp) if tp + fp else 0
        f1 = 2 * r * p / (r + p) if r + p else 0
        L.append(f"| {t} | {g} | {tp} | {fp} | {r:.1%} | {p:.1%} | {f1:.3f} |")
    r = TP / TG if TG else 0; p = TP / (TP + FP) if TP + FP else 0
    L.append(f"| 합계 | {TG} | {TP} | {FP} | {r:.1%} | {p:.1%} | {2 * r * p / (r + p) if r + p else 0:.3f} |")
    L += ["", f"참고 점수(채점기 가정: 45 x 재현율 + 35 x 정밀도, 시간 제외): {45 * r + 35 * p:.1f} / 80"]
    return "\n".join(L) + "\n"
