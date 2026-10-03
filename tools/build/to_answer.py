"""data/samples 의 실측 라벨 -> 요강 붙임4 스키마 정답셋 (data/answers/).

요강 기준으로 나눈다.
  answer_result.json        적격평가 대상 '주요 탐지 유형' 4종 (HOMOGLYPH·JAMO·TRANSPARENT·OFFSCREEN)
  answer_result_extra.json  추가 유형 (technique "ETC" 고정, 유형명은 extra_finding)
  negatives.json            DECOY: 숨김 신호는 있지만 광고가 아닌 정상 요소. 여기에 걸리면 오탐

검출 1건 = (url + location + technique). 한 요소에 기법이 겹치면 기법별로 객체를 따로 만든다(요강 붙임4).
url 은 샘플을 잘라 온 실제 페이지 주소, location 은 잘라 낸 조각(html) 안의 유일 선택자다.
그래서 이 파일로는 조각 단위 채점만 된다. 페이지 단위 채점은 mocksite 에 조각을 심은 뒤 그 주소로 다시 만든다.

사용: python tools/build/to_answer.py
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SAMPLES = ROOT / "data" / "samples"
OUT = ROOT / "data" / "answers"
MAIN4 = ("HOMOGLYPH", "JAMO", "TRANSPARENT", "OFFSCREEN")
URL_RE = re.compile(r"https?://[^\s)]+")


def load(name):
    return yaml.safe_load((SAMPLES / name).read_text(encoding="utf-8"))


def page_url(item):
    m = URL_RE.search(item["source"])
    if not m:
        sys.exit(f"{item['id']}: source 에 URL 이 없다: {item['source']}")
    return m.group(0)


def finding(item, technique, extra=None):
    f = {
        "id": f"{item['id']}_{extra or technique}",
        "url": page_url(item),
        "is_violation": True,
        "location": item["expected_location"],
        "evidence_text": item["evidence_text"],
        "technique": technique,
    }
    if extra:
        f["extra_finding"] = extra
    return f


def doc(source_files, findings, key="findings"):
    return {"meta": {"topic": "TOPIC", "kind": "answer", "source": source_files}, key: findings}


def main():
    decoy, etc, combo = load("decoy.yaml"), load("etc.yaml"), load("combo_real.yaml")

    main4 = [finding(i, code) for i in combo for code in i["label_codes"]]
    extra = [finding(i, "ETC", i["extra_finding"]) for i in etc]
    extra += [finding(i, "ETC", name) for i in combo for name in i["extra_findings"]]
    neg = [{"id": i["id"], "url": page_url(i), "location": i["expected_location"],
            "evidence_text": i["evidence_text"], "subtype": i["subtype"]} for i in decoy]

    for f in main4:
        assert f["technique"] in MAIN4, f
    for name, fs in (("main4", main4), ("extra", extra), ("neg", neg)):
        ids = [f["id"] for f in fs]
        assert len(ids) == len(set(ids)), f"{name}: id 중복"

    OUT.mkdir(exist_ok=True)
    out = {
        "answer_result.json": doc(["combo_real.yaml"], main4),
        "answer_result_extra.json": doc(["etc.yaml", "combo_real.yaml"], extra),
        "negatives.json": doc(["decoy.yaml"], neg, key="negatives"),
    }
    for name, d in out.items():
        # 요강과 같은 UTF-8(BOM 없음)
        text = json.dumps(d, ensure_ascii=False, indent=2) + "\n"
        (OUT / name).write_text(text, encoding="utf-8", newline="\n")

    c4 = Counter(f["technique"] for f in main4)
    print("answer_result.json       ", len(main4), {k: c4.get(k, 0) for k in MAIN4})
    print("answer_result_extra.json ", len(extra), dict(Counter(f["extra_finding"] for f in extra).most_common()))
    print("negatives.json           ", len(neg), dict(Counter(f["subtype"] for f in neg)))
    only_extra = sum(1 for i in combo if not i["label_codes"])
    print(f"combo {len(combo)} 중 4종 코드가 없어 result_extra 에만 들어간 요소 {only_extra}")


if __name__ == "__main__":
    main()
