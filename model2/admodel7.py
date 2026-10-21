"""v7 후보 광고 판정기 (10-18). admodel5.AdSel(v5·v6) 에 두 가지를 켜고 끌 수 있게 한 것.

근거(진행보고서 7-18·7-19절, 팀원 새 사이트 진단 + 개발 데이터 check_cues.py):
  가) 글자 정규화: v6 글자 판정기는 원문 n-gram 과 복원(restore: NFKC·보이지 않는 글자 제거·라틴 닮은꼴·자모 조합) n-gram 을
      나란히 쓴다. 원문 쪽은 개발 데이터에 나온 변형 문자 꼴 자체를 광고 단서로 배워, 처음 보는 꼴의 변형 문자로 옮겨 가지 않는다.
      text="restored" 면 복원 글자만 쓰고, cue_norm 이면 내용 단서(URL·메신저·전화·숫자 비율)도 복원 글자에서 잰다(전각 숫자 전화번호 등).
  나) 연락 단서 의존 줄이기: 개발 숨김 광고의 89% 가 연락 단서를 가져 판정기가 「단서 없음 = 광고 아님」에 기댄다.
      drop=p 면 HGB 학습 때 단서(열 0~4)가 있는 줄의 비율 p 를 골라 단서를 0 으로 지운 사본을 더한다(광고·비광고 모두, 사전 비율 유지).
      검사 때는 바꾸지 않는다.
"""
import random

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from textfeat import restore
import re

from train2 import AdModel, SEED, side_feats, URL_RE, HANDLE_RE, PHONE_RE

CUE = [0, 1, 2, 3, 4]  # side_feats 열: 외부 링크, 상대 링크, URL 꼴, 메신저, 전화
PUBLIC = (".go.kr", ".ac.kr", ".re.kr", ".mil.kr", "korea.kr")


def _public(h):
    from urllib.parse import urlparse
    if not h or not h.startswith(("http://", "https://", "//")):
        return False
    host = (urlparse(h if not h.startswith("//") else "http:" + h).hostname or "").lower()
    return host.endswith(PUBLIC) or host in ("korea.kr", "go.kr")


def ui_skip(rows):
    """10-18 2차(진행보고서 7-19절): 광고가 아닌 화면 부품을 규칙 결과(rt)에서 뺀다. 줄을 고친 개수를 돌려준다.
    (1) option·optgroup 은 OF·TR 에서 뺀다. (2) 공공 도메인 링크, 그리고 공공 링크 3개 이상만 품은 묶음은 모든 기법에서 뺀다."""
    from collections import defaultdict
    kids = defaultdict(list)
    for r in rows:
        kids[(r["sid"], r["parent"])].append(r)

    def links(r, acc):
        for c in kids[(r["sid"], r["i"])]:
            if c.get("href"):
                acc.append(c["href"])
            links(c, acc)
        return acc

    n = 0
    for r in rows:
        if not r.get("rt"):
            continue
        rt = dict(r["rt"])
        if r["tag"] in ("option", "optgroup"):
            rt.pop("OFFSCREEN", None)
            rt.pop("TRANSPARENT", None)
        if _public(r.get("href")):
            rt = {}
        else:
            ls = links(r, [])
            if len(ls) >= 3 and all(_public(h) for h in ls):
                rt = {}
        if rt != r["rt"]:
            r["rt"] = rt
            n += 1
    return n


class TextR(AdModel):
    """복원 글자 n-gram 만 쓰는 글자 판정기."""

    def _x(self, texts, fit):
        res = [restore(t).lower() for t in texts]
        if fit:
            self.v2 = TfidfVectorizer(analyzer="char_wb", ngram_range=(1, 3), min_df=2, max_features=80000, sublinear_tf=True)
            return self.v2.fit_transform(res)
        return self.v2.transform(res)

    def fit(self, rows):
        use = [r for r in rows if not r["t_skip"]]
        y = np.array([int(any(r["lab"].values())) for r in use])
        self.lr = LogisticRegression(C=self.C, max_iter=3000, class_weight="balanced", random_state=SEED)
        self.lr.fit(self._x([r["text"] for r in use], True), y)
        return self


def strip_text(t):
    """연락 단서(URL·메신저·전화) 부분을 글자에서 지운다. URL·메신저가 든 낱말은 통째로, 메신저 낱말 뒤 아이디 꼴 낱말도 함께."""
    t = PHONE_RE.sub(" ", t)
    out, skip = [], False
    for w in t.split():
        if skip and re.fullmatch(r"[@:]?[A-Za-z0-9_.\-]{2,}", w):
            skip = False
            continue
        skip = False
        if URL_RE.search(w):
            continue
        if HANDLE_RE.search(w):
            skip = True
            continue
        out.append(w)
    return " ".join(out)


def strip_copies(use, p):
    """다) 10-18: 연락 단서가 있는 줄(광고·비광고 모두)의 비율 p 를 골라, 글자에서 단서를 지우고 링크를 뺀 사본을 만든다.
    사본은 원본과 같은 표본 id 를 가져 학습 안 3겹 나눔에서 원본과 같은 쪽에 들어간다(사본-원본 새는 것 막음).
    부르는 쪽(fit)이 학습 몫만 넘기므로 평가 몫에는 사본이 생기지 않는다."""
    has = [k for k, c in enumerate(side_feats(use)[:, CUE].max(axis=1) > 0) if c]
    pick = sorted(random.Random(SEED).sample(has, int(round(len(has) * p))))
    out = []
    for k in pick:
        t = strip_text(use[k]["text"])
        if len(t) >= 2:
            out.append(dict(use[k], text=t, href="", i=-1 - k))
    return out


_TOK = re.compile(r"[가-힣a-z0-9]{2,}")


def _toks(t):
    t = restore(t).lower()
    w = _TOK.findall(t)
    c = re.sub(r"[^가-힣a-z0-9]", "", t)
    return w, [c[k:k + 2] for k in range(len(c) - 1)]


def add_ctx(rs):
    """10-19 바)(진행보고서 7-33절): 쪽마다 그 쪽 글자로만 「이 요소의 낱말·두 자 묶음 중 쪽의 다른 곳에 안 나오는 비율」을 r["ctx"] 에 단다.
    쪽 글자 = 같은 sid 의 잎 줄(다른 줄의 부모가 아닌 줄, i >= 0). 자기 몫(자기 글자의 개수)은 빼고 센다. 낱말이 없으면 -1.
    rs 를 그대로 고쳐 돌려준다(이미 단 줄은 건드리지 않는다)."""
    from collections import Counter, defaultdict
    by = defaultdict(list)
    for r in rs:
        if r.get("i", 0) >= 0:
            by[r["sid"]].append(r)
    for g in by.values():
        if all("ctx" in r for r in g):
            continue
        par = {r["parent"] for r in g}
        pw, pc = Counter(), Counter()
        for r in g:
            if r["i"] not in par:
                w, c = _toks(r["text"])
                pw.update(w)
                pc.update(c)
        for r in g:
            if "ctx" in r:
                continue
            w, c = _toks(r["text"])
            out = []
            for own, page in ((Counter(w), pw), (Counter(c), pc)):
                out.append(sum(1 for x, n in own.items() if page[x] - n <= 0) / len(own) if own else -1.0)
            r["ctx"] = out
    return rs


class AdSel7:
    def __init__(self, C, cols, text="both", cue_norm=False, drop=0.0, strip=0.0, lex=None, lexmod="adlex", ctx=False):
        self.C, self.cols, self.text_mode, self.cue_norm, self.drop = C, cols, text, cue_norm, drop
        self.ctx = ctx  # 10-19 바) 주제 어긋남 특징(7-33절). False 면 v8c 와 같음
        self.strip = strip
        self.lexmod = lexmod
        self.lex = lex  # 10-19 라) 갈래 사전 표지(adlex.LEX 의 갈래 이름 목록). None 이면 안 씀(v7c 와 같음)

    def _lexf(self, rs):
        if not getattr(self, "lex", None):
            return np.zeros((len(rs), 0))
        import importlib
        cats = importlib.import_module(getattr(self, "lexmod", "adlex")).cats  # 10-19 v8c 는 adlex2(7-29절)
        return np.array([[1.0 if k in c else 0.0 for k in self.lex] for c in (cats(r["text"]) for r in rs)]).reshape(len(rs), len(self.lex))

    def _ctxf(self, rs):
        if not getattr(self, "ctx", False):
            return np.zeros((len(rs), 0))
        add_ctx(rs)
        return np.array([r.get("ctx", [-1.0, -1.0]) for r in rs]).reshape(len(rs), 2)

    def _tm(self):
        return TextR(self.C) if self.text_mode == "restored" else AdModel(self.C)

    def _side(self, rs):
        if self.cue_norm:
            sf = side_feats(rs)
            sn = side_feats([dict(r, text=restore(r["text"])) for r in rs])
            sf[:, [2, 3, 4, 6]] = sn[:, [2, 3, 4, 6]]  # 링크 열(0·1)은 href 라 그대로
            return sf
        return side_feats(rs)

    def fit(self, rs):
        if getattr(self, "ctx", False):
            add_ctx(rs)  # 걸러지기·사본 만들기 전에 전체 쪽으로 계산(사본은 dict 복사로 원본 값을 물려받는다)
        use = [r for r in rs if not r["t_skip"]]
        if self.strip > 0:
            use = use + strip_copies(use, self.strip)
        y = np.array([int(any(r["lab"].values())) for r in use])
        ss = sorted({r["sid"] for r in use})
        part = {s: k % 3 for k, s in enumerate(ss)}
        pk = np.array([part[r["sid"]] for r in use])
        oof = np.zeros(len(use))
        for k in range(3):
            oof[pk == k] = self._tm().fit([r for r, p in zip(use, pk) if p != k]).score([r for r, p in zip(use, pk) if p == k])
        self.text = self._tm().fit(use)
        X = np.hstack([oof[:, None], self._side(use)[:, self.cols], self._lexf(use), self._ctxf(use)])
        if self.drop > 0:
            ci = [1 + self.cols.index(c) for c in CUE if c in self.cols]
            has = np.where(X[:, ci].max(axis=1) > 0)[0]
            rng = random.Random(SEED)
            pick = np.array(sorted(rng.sample(list(has), int(round(len(has) * self.drop)))), dtype=int)
            Xa = X[pick].copy()
            Xa[:, ci] = 0.0
            X, y = np.vstack([X, Xa]), np.concatenate([y, y[pick]])
        self.hgb = HistGradientBoostingClassifier(learning_rate=0.05, max_leaf_nodes=15, max_iter=300, class_weight="balanced",
                                                  random_state=SEED).fit(X, y)
        return self

    def score(self, rs):
        return self.hgb.predict_proba(np.hstack([self.text.score(rs)[:, None], self._side(rs)[:, self.cols], self._lexf(rs), self._ctxf(rs)]))[:, 1]
