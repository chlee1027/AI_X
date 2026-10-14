"""추가 유형(result_extra.json, technique "ETC" + extra_finding) 5종.

  ZERO_WIDTH     낱말 안(앞뒤가 글자)에 보이지 않는 글자(Cf)가 있고, 지운 뒤 내용 판정이 광고
  ENCODING       href 의 퍼센트 인코딩(비 ASCII) 또는 숫자 엔티티를 풀면 광고 문구
  LINK_CLOAKING  외부 링크인데 앵커 글자에 그 주소가 없고, 주소(+글자)의 내용 판정이 광고. 목적지는 방문 안 함
  META_CLOAKING  meta(description·og·keywords) 값이 광고
  CSS_CONTENT    ::before/::after content 글자가 광고

  python extra.py cv | test
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from urllib.parse import unquote, urlsplit

from sklearn.model_selection import GroupKFold

from common import OUT, load_all, site_of
from detector import Content, is_ext, pages, train_texts

sys.stdout.reconfigure(encoding="utf-8")
EXTRA = ("ZERO_WIDTH", "ENCODING", "LINK_CLOAKING", "META_CLOAKING", "CSS_CONTENT")
CF_IN_WORD = re.compile(r"\w[­​-‏⁠-⁤﻿]+\w")
PCT_NONASCII = re.compile(r"(?:%[89a-fA-F][0-9a-fA-F]){2,}")
CSS_URL = re.compile(r"url\([^)]*\)", re.I)
# 실제 누리집 3차 측정에서 정한 두 처리(10-14). 끄면 이전 판과 같다
ENC_SEG_ONLY = True   # ENCODING: 호스트를 빼고 경로·쿼리를 풀어 판정(주소 모양만으로 점수가 오르지 않게. 지도 주소의 한글 이름 「경기도청」은 광고가 아니다)
CSS_STRIP_URL = True  # CSS_CONTENT: content 의 url(아이콘 그림)은 글자가 아니므로 빼고 판정
# LINK_CLOAKING: 한 페이지에서 같은 앵커 글자(「바로가기」)가 바깥 호스트 LINK_DIR_HOSTS 곳 이상을 가리키면 관련 사이트 목록으로 본다
# (실측 6차 인천시 자매도시 표). 정답 86건 가운데 이 꼴은 0건이다. 0 이면 끈다
LINK_DIR_HOSTS = 3
LETTER = re.compile(r"[가-힣ㄱ-ㅎㅏ-ㅣA-Za-z]")


def gold_extra(it):
    if it["cat"] == "ETC" and it.get("extra_finding") in EXTRA:
        return [it["extra_finding"]]
    if it["cat"] == "COMBO":
        return [x for x in (it.get("extra_findings") or []) if x in EXTRA]
    return []


class LinkModel:
    """외부 링크 하나를 클로킹으로 볼지: 주소(호스트·경로) 글자 조각 + 앵커 글자 조각 로지스틱 회귀."""

    def __init__(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.linear_model import LogisticRegression
        self.vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), min_df=2, sublinear_tf=True)
        self.clf = LogisticRegression(max_iter=2000, C=2.0, class_weight="balanced")

    @staticmethod
    def text(e):
        u = urlsplit(e["href"])
        host = (u.hostname or "").lower()
        return f"H:{host} P:{u.path[:80]} Q:{'1' if u.query else '0'} T:{e['text'].strip()[:60]} X:{'puny' if 'xn--' in host else ''}"

    def fit(self, items, feat):
        X, y = [], []
        for it in items:
            fr = feat[it["id"]]
            gold = fr["exp_idx"] if "LINK_CLOAKING" in gold_extra(it) else None
            for e in fr["els"]:
                if e["tag"] == "a" and is_ext(e.get("href") or "", it["site"]):
                    X.append(self.text(e)); y.append(1 if e["i"] == gold else 0)
        if sum(y) == 0:
            self.clf = None
            return self
        self.clf.fit(self.vec.fit_transform(X), y)
        return self

    def proba(self, els):
        if not els or self.clf is None:
            return [0.0] * len(els)
        return self.clf.predict_proba(self.vec.transform([self.text(e) for e in els]))[:, 1]


class Extra:
    def __init__(self, content, th, link=None):
        self.c = content
        self.th = th
        self.link = link

    def detect(self, fr, site):
        cands = []
        link_dir = set()
        if LINK_DIR_HOSTS:
            t2h = defaultdict(set)
            # 공공 기관 도메인도 센다(자매도시 표는 외국 시청 주소가 대부분이다)
            for e in fr["els"]:
                h = site_of(e.get("href") or "") if (e.get("href") or "").startswith("http") else ""
                if e["tag"] == "a" and h and h != site and not h.endswith("." + site) and not site.endswith("." + h):
                    t2h[" ".join(e["text"].split())].add(h)
            link_dir = {e["i"] for e in fr["els"] if e["tag"] == "a" and len(t2h.get(" ".join(e["text"].split()), ())) >= LINK_DIR_HOSTS}
        for e in fr["els"]:
            own = e["own"]
            if own.strip() and CF_IN_WORD.search(own):
                cands.append((e["i"], "ZERO_WIDTH", e["text"]))
            href = e.get("href") or ""
            if href and PCT_NONASCII.search(href):
                u = urlsplit(href)
                dec = unquote(u.path + " " + u.query).replace("&", " ").replace("=", " ") if ENC_SEG_ONLY else unquote(href)
                cands.append((e["i"], "ENCODING", dec))
            if e["tag"] == "a" and is_ext(href, site) and self.link is not None:
                host = (urlsplit(href).hostname or "").lower()
                if host and host not in e["text"].lower() and e["i"] not in link_dir:
                    cands.append((e["i"], "LINK_CLOAKING", e))
            if e.get("attr_content") and re.search(r"description|keywords|title", e.get("meta_key", ""), re.I):
                cands.append((e["i"], "META_CLOAKING", e["attr_content"]))
            if e.get("pseudo"):
                ps = CSS_URL.sub(" ", e["pseudo"]) if CSS_STRIP_URL else e["pseudo"]
                if not CSS_STRIP_URL or LETTER.search(ps):
                    cands.append((e["i"], "CSS_CONTENT", ps))
        if not cands:
            return []
        out = set()
        tc = [c for c in cands if c[1] != "LINK_CLOAKING"]
        lc = [c for c in cands if c[1] == "LINK_CLOAKING"]
        for (i, t, _), p in list(zip(tc, self.c.proba([c[2] for c in tc]))) + list(zip(lc, self.link.proba([c[2] for c in lc]) if lc else [])):
            if p >= self.th[t]:
                out.add((i, t))
        return sorted(out)


def evaluate(items, feat, preds):
    by_t = defaultdict(Counter)
    neg = Counter()
    for grp in pages(items):
        it = grp[0]
        P = set(preds.get(it["id"], []))
        G = set()
        for x in grp:
            G |= {(feat[x["id"]]["exp_idx"], t) for t in gold_extra(x)}
        for g in G:
            by_t[g[1]]["gold"] += 1; by_t[g[1]]["tp"] += g in P
        for p in P - G:
            by_t[p[1]]["fp"] += 1
        if not it["positive"]:
            neg[it["cat"] + "_pages"] += 1
            neg[it["cat"] + "_fp"] += bool(P)
    return by_t, neg


def table(by_t, neg):
    L = ["| 유형 | 정답 건 | 맞힘 | 오답 출력 | 재현율 | 정밀도 |", "|---|---:|---:|---:|---:|---:|"]
    for t in EXTRA:
        v = by_t[t]
        g, tp, fp = v["gold"], v["tp"], v["fp"]
        L.append(f"| {t} | {g} | {tp} | {fp} | {tp / g:.1%} | {tp / (tp + fp) if tp + fp else 0:.1%} |" if g else
                 f"| {t} | 0 | 0 | {fp} | - | - |")
    L.append("")
    L.append(f"음성 페이지 오탐: DECOY {neg['DECOY_fp']}/{neg['DECOY_pages']}, TR 음성 {neg['TR_NEG_fp']}/{neg['TR_NEG_pages']}")
    return "\n".join(L)
