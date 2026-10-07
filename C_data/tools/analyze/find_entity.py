"""받은 원문에서 숫자 엔티티(&#52852; 꼴)로 쓴 한글 도박 광고가 든 가장 깊은 요소를 찾는다.

원문 위치를 그대로 쓰려고 html.parser 로 여는 태그의 원문 오프셋을 따라간다(디코딩된 DOM 으로는 엔티티가 사라진다).
한 요소의 엔티티 덩어리를 풀었을 때 도박 어휘가 있어야 후보로 둔다.

갈래:
  takeover : 페이지 제목(디코딩 뒤)에 도박 어휘가 있다 = 넘어간 도메인에서 페이지 전체가 도박 홍보 (가)
  injected : 제목은 정상이고 링크 목록·본문 링크 앵커에만 있다 (나)

사용: python tools/analyze/find_entity.py
출력: data/raw/entity/entity_candidates.json
"""
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAGES = ROOT / "data" / "raw" / "entity" / "pages"
OUT = ROOT / "data" / "raw" / "entity" / "entity_candidates.json"

# 한글 음절(U+AC00~U+D7A3 = 44032~55203) 숫자 엔티티가 공백·문장부호를 끼고 이어진 덩어리
HANGUL_ENT = r"&#(?:4[4-9]\d{3}|5[0-4]\d{3}|55[01]\d{2}|5520[0-3]);"
RUN = re.compile(rf"{HANGUL_ENT}(?:(?:[\s\d%.,!?:/()\-+]|&#\d+;|&nbsp;|&amp;)*{HANGUL_ENT})*")
GAMBLING = re.compile(r"토토|카지노|바카라|슬롯|홀덤|먹튀|파워볼|놀이터|베팅|배팅|메이저사이트|꽁머니|에볼루션|스포츠북|첫충|"
                      r"룰렛|블랙잭|포커|사설|입플|롤링|환전|도박|겜블|갬블")
PHONE = re.compile(r"01[016789][\s\-–.]*\d{3,4}[\s\-–.]*\d{4}")
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
SKIP = {"script", "style", "title", "head", "noscript", "textarea", "option", "svg"}


class Tracker(HTMLParser):
    """여는 태그의 원문 오프셋과 조상 줄을 기록한다."""

    def __init__(self, raw):
        super().__init__(convert_charrefs=False)
        self.raw = raw
        self.line_off = [0]
        for m in re.finditer("\n", raw):
            self.line_off.append(m.end())
        self.stack = []  # (tag, attrs, start, end_of_start_tag)
        self.elements = []  # (tag, attrs, start, start_tag_end, end, chain)

    def off(self):
        line, col = self.getpos()
        return self.line_off[line - 1] + col

    def handle_starttag(self, tag, attrs):
        start = self.off()
        text = self.get_starttag_text() or ""
        if tag in VOID:
            return
        self.stack.append((tag, dict(attrs), start, start + len(text)))

    def handle_endtag(self, tag):
        end = self.off()
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                close = self.raw.find(">", end) + 1
                t, a, s, se = self.stack[i]
                chain = [(x[0], x[1]) for x in self.stack[:i]]
                self.elements.append((t, a, s, se, close, chain))
                del self.stack[i:]
                return


def sel_part(tag, attrs):
    part = tag
    if attrs.get("id") and re.fullmatch(r"[A-Za-z][\w-]*", attrs["id"]):
        return part + "#" + attrs["id"]
    for c in (attrs.get("class") or "").split():
        if re.fullmatch(r"-?[A-Za-z_][\w-]*", c):
            part += "." + c
    return part


def page_title(raw):
    m = re.search(r"<title[^>]*>(.*?)</title>", raw, re.S | re.I)
    return html.unescape(m.group(1)).strip() if m else ""


def main():
    cands = []
    for f in sorted(PAGES.glob("*.html")):
        raw = f.read_bytes().decode("utf-8", "replace")
        title = page_title(raw)
        kind = "takeover" if GAMBLING.search(title) else "injected"
        t = Tracker(raw)
        try:
            t.feed(raw)
        except Exception as e:  # 깨진 원문은 건너뛴다
            print(f.name, "parse error", e)
            continue
        runs = [(m.start(), m.end(), m.group(0)) for m in RUN.finditer(raw)]
        seen = set()
        for s, e, ent in runs:
            dec = html.unescape(ent)
            if not GAMBLING.search(dec):
                continue
            # 이 덩어리를 감싸는 가장 깊은(가장 짧은) 요소
            inner = [x for x in t.elements if x[3] <= s and e <= x[4] and x[0] not in SKIP]
            if not inner or any(c[0] in SKIP for c in min(inner, key=lambda x: x[4] - x[2])[5]):
                continue
            el = min(inner, key=lambda x: x[4] - x[2])
            if el[2] in seen:
                continue
            seen.add(el[2])
            outer = raw[el[2]:el[4]]
            text = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", outer))).strip()
            cands.append({
                "file": f.name, "title": title, "kind": kind, "tag": el[0], "attrs": el[1],
                "href": el[1].get("href"), "chain": [sel_part(*c) for c in el[5]],
                "chain_raw": el[5], "outer": outer, "evidence": ent, "decoded": dec, "text": text,
                "phone": bool(PHONE.search(text)), "length": len(outer),
            })
    OUT.write_text(json.dumps(cands, ensure_ascii=False, indent=1), encoding="utf-8")
    by = {}
    for c in cands:
        by.setdefault((c["file"], c["kind"]), 0)
        by[(c["file"], c["kind"])] += 1
    for k, v in sorted(by.items()):
        print(k[1], k[0], v)


if __name__ == "__main__":
    main()
