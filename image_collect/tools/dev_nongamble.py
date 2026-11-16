"""1차 dev_data 양성 항목 중 도박 외 불법 낱말이 있는 페이지를 종류별로 모은다 -> logs/dev_nongamble.json

dev_data 만 읽는다(공모전 시험 몫은 건드리지 않는다). 낱말은 사람이 본 스팸 표지이고 씨앗을 고르는 데만 쓴다. 라벨은 이미지를 보고 따로 붙인다.
출력: {종류: {url: 맞은 낱말 수}}
"""
import glob
import html
import json
import os
import re
from collections import defaultdict

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
DEV = os.path.join(HERE, "..", "..", "v2_20261017", "dev_data")
OUT = os.path.join(HERE, "..", "logs", "dev_nongamble.json")
KW = {
    "loan": r"내구제|작업대출|급전|일수|소액결제|휴대폰대출|신용불량|무직자대출|상품권\s*현금화|정보이용료|유심\s*개통|비대면대출|대출\s*상담",
    "forgery": r"대리시험|대리\s*응시|위조|졸업증명서|성적증명서|증명서\s*제작|학위증|운전면허증\s*제작|신분증\s*제작|여권\s*제작|토익\s*대리|자격증\s*대행",
    "drug": r"비아그라|시알리스|레비트라|낙태약|미프진|정력제|필름형|발기부전|조루약|필로폰|대마초|졸피뎀|스테로이드\s*판매|다이어트\s*약\s*구매",
    "invest": r"리딩방|주식\s*리딩|코인\s*리딩|해외선물|선물\s*대여|수익\s*보장|원금\s*보장|고수익\s*투자|FX\s*마진|마진\s*거래\s*리딩",
    "adult": r"060|폰팅|출장안마|출장\s*마사지|조건만남|오피\s*사이트|콜걸|성인\s*채팅|유흥",
    "etc": r"흥신소|심부름센터|불법\s*촬영물|계정\s*판매|통장\s*매입|대포통장|대포폰|백링크\s*판매",
}
KW = {k: re.compile(v, re.I) for k, v in KW.items()}


def items_of(d):
    if isinstance(d, list):
        return d
    if isinstance(d, dict):
        for v in d.values():
            if isinstance(v, list):
                return v
    return []


def main():
    out = defaultdict(lambda: defaultdict(int))
    n = 0
    for f in glob.glob(os.path.join(DEV, "*", "*.yaml")):
        for it in items_of(yaml.safe_load(open(f, encoding="utf-8"))):
            if not isinstance(it, dict) or not it.get("is_positive"):
                continue
            n += 1
            t = " ".join(str(it.get(k, "")) for k in ("html", "evidence_text", "text"))
            s = " ".join(str(it.get(k, "")) for k in ("source", "page_url", "url"))
            urls = [html.unescape(m.rstrip(".,")) for m in re.findall(r"https?://[^\s'\"()]+", s)]
            for cat, rx in KW.items():
                hits = len(rx.findall(t))
                if hits:
                    for u in urls:
                        out[cat][u] += hits
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print("positive items", n)
    for c, d in out.items():
        print(c, "pages", len(d))


if __name__ == "__main__":
    main()
