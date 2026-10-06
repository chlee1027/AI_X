"""받은 게시판 목록 페이지에서 키릴·그리스 위장 제목을 찾아 사람 2 양식 행으로 만든다 (2026-10-06, 역할 C).

판정: 한 토큰 안에 키릴·그리스 글자가 라틴·숫자와 섞여 있거나(.cом, CΟΜ), 키릴·그리스 글자 2개 이상으로
라틴 단어를 흉내 낸 것(нσиgвσ). 문장 글자의 절반 이상이 키릴이면 러시아어 스팸이라 뺀다(사람 2 규칙과 같음).
양식: html = 제목 <a> 조각, expected_location = 조각 안 유일 선택자, page_location = 원본 페이지 유일 선택자.
휴대폰 번호는 가운데 자리를 같은 모양의 0 으로 가린다. 캠페인은 원본 행과 같은 위장 문자열이 있으면 그 키를 쓴다.
사용: python tools/analyze/scan_cyrillic.py <pages 폴더> <원본 homoglyph_real_test.yaml> <출력 add_cyrillic.yaml>
"""
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

import lxml.html
import yaml


def cg(c):
    o = ord(c)
    return c.isalpha() and (0x0370 <= o <= 0x03FF or 0x0400 <= o <= 0x04FF or 0x1F00 <= o <= 0x1FFF)


def hit_tokens(text):
    letters = [c for c in text if c.isalpha() and not ("가" <= c <= "힣" or "ㄱ" <= c <= "ㆎ")]
    if letters and sum(0x0400 <= ord(c) <= 0x04FF for c in letters) * 2 >= len(letters):
        return []
    out = []
    for t in re.split(r"[\s【】\[\]［］（）()<>＜＞|｜:：/@＠\"'“”,]+", text):
        n = sum(cg(c) for c in t)
        if not n:
            continue
        mixed = any(c.isascii() and c.isalnum() for c in t)
        if mixed or n >= 2:
            out.append(t)
    return out


def masked_digit(c):
    if c.isascii():
        return "0" if c.isdigit() else c
    name = unicodedata.name(c, "")
    for d in ("ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE"):
        if name.endswith("DIGIT " + d):
            try:
                return unicodedata.lookup(name[: -len(d)] + "ZERO")
            except KeyError:
                return "0"
    return c


def digit_of(c):
    n = unicodedata.normalize("NFKC", c)
    if n in "Oo":
        return "0"
    if n in "lI":
        return "1"
    if len(n) == 1 and n.isdigit():
        return n
    return None


def mask_phone(s):
    pos = [(i, digit_of(c)) for i, c in enumerate(s) if digit_of(c) is not None]
    runs, run = [], []
    for i, d in pos:
        if run and (i - run[-1][0] > 4 or re.search(r"[가-힣A-Za-z]", s[run[-1][0] + 1:i])):
            runs.append(run)
            run = []
        run.append((i, d))
    if run:
        runs.append(run)
    chars = list(s)
    for run in runs:
        g = "".join(d for _, d in run)
        m = re.search(r"01[016789]\d{7,8}", g)
        if m:
            for k in range(m.start() + 3, m.end() - 4):
                i = run[k][0]
                chars[i] = masked_digit(chars[i]) if chars[i] not in "OolI" else chars[i]
    return "".join(chars)


def css_path(el):
    parts = []
    while el is not None and el.tag not in ("html", "body"):
        p = el.getparent()
        same = [x for x in p.iterchildren(el.tag)] if p is not None else [el]
        cls = (el.get("class") or "").split()
        part = el.tag + (f".{cls[0]}" if cls and re.fullmatch(r"[\w-]+", cls[0]) else "")
        if len(same) > 1:
            part += f":nth-of-type({same.index(el) + 1})"
        parts.append(part)
        el = p
    return " > ".join(reversed(parts))


def main(pages_dir, orig_yaml, out_yaml):
    pages_dir = Path(pages_dir)
    orig = yaml.safe_load(Path(orig_yaml).read_text(encoding="utf-8"))
    known = {}
    for r in orig:
        for t in hit_tokens(r["evidence_text"]):
            core = "".join(c for c in t if cg(c))
            known.setdefault(core, Counter())[r["campaign"]] += 1
    have = {re.sub(r"\s+", "", r["evidence_text"]) for r in orig}
    log = {}
    if (pages_dir / "log.jsonl").exists():
        for line in (pages_dir / "log.jsonl").read_text(encoding="utf-8").splitlines():
            d = json.loads(line)
            if d.get("page_id"):
                log[d["page_id"]] = (d["url"], pages_dir / f"{d['page_id']}.html")
    else:  # 역할 C 기존 원문: <id>_<variant>.html 옆에 같은 이름 .json(url)
        for h in sorted(pages_dir.rglob("*.html")):
            meta = h.with_suffix(".json")
            if meta.exists():
                try:
                    log[h.stem] = (json.loads(meta.read_text(encoding="utf-8"))["url"], h)
                except (OSError, ValueError, KeyError):
                    pass
    rows, seen = [], set()
    for pid, (url, path) in log.items():
        if url.endswith((".css", ".js")):
            continue
        try:
            raw = path.read_bytes()
        except OSError as e:  # 백신이 막은 파일(감염 페이지)은 열지 않고 건너뛴다
            print("열 수 없어 건너뜀:", url, e.errno)
            continue
        m = re.search(rb"charset=[\"']?([\w-]+)", raw[:4000])
        enc = m.group(1).decode().lower() if m else "utf-8"
        enc = "cp949" if enc in ("euc-kr", "ks_c_5601-1987", "ksc5601") else enc
        try:
            doc = lxml.html.document_fromstring(raw.decode(enc if enc not in ("utf8",) else "utf-8", "replace"))
        except (lxml.etree.ParserError, LookupError):
            continue
        for a in doc.iter("a"):
            text = re.sub(r"\s+", " ", a.text_content()).strip()
            toks = hit_tokens(text)
            if not toks or len(text) < 6:
                continue
            key = re.sub(r"\s+", "", text)
            if key in have or key in seen:
                continue
            seen.add(key)
            # 가장 깊은, 글을 다 담은 요소
            target = a
            for el in a.iter():
                if el is not a and isinstance(el.tag, str) and re.sub(r"\s+", " ", el.text_content()).strip() == text:
                    target = el
            frag = lxml.html.tostring(a, encoding="unicode", with_tail=False)
            loc = target.tag + (f".{(target.get('class') or '').split()[0]}" if target is not a and (target.get("class") or "").split() else "")
            wrap = lxml.html.fromstring(f"<div>{frag}</div>")
            if len(wrap.cssselect(loc)) != 1:
                loc = "a"
            parts = css_path(target).split(" > ")
            ploc = next((" > ".join(parts[k:]) for k in range(len(parts) - 1, -1, -1)
                         if len(doc.cssselect(" > ".join(parts[k:]))) == 1), None)
            if ploc is None:
                continue
            core = "".join(c for c in toks[0] if cg(c))
            camp = known[core].most_common(1)[0][0] if core in known else "token:cg-" + "".join(
                unicodedata.normalize("NFKC", c).lower() for c in toks[0] if c.isascii() and c.isalnum() or cg(c))[:20]
            ev = mask_phone(text)
            host = url.split("/")[2]
            rows.append({
                "id": "HG-RT-NEW", "category": "HOMOGLYPH", "subtype": "cyrillic_greek",
                "html": mask_phone(frag), "css": "", "evidence_text": ev, "expected_location": loc,
                "is_positive": True, "extra_finding": None,
                "source": f"직접 수집(공공 웹사이트) · {url}", "source_type": "real", "split": "test",
                "page_location": ploc, "origin": {"url": url, "host": host, "page_id": pid},
                "campaign": camp, "tier": "A",
                "notes": f"2026-10-06 역할 C 보충(키릴·그리스). 위장 토큰: {' '.join(toks)}",
            })
    Path(out_yaml).write_text(yaml.safe_dump(rows, allow_unicode=True, sort_keys=False, width=200), encoding="utf-8")
    print(len(rows), ascii(Counter(r["campaign"] for r in rows).most_common(20)))


if __name__ == "__main__":
    main(*sys.argv[1:4])
