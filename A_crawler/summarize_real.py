"""out_real/<호스트>/ 결과를 모아 사이트별 출력 수와 사람이 가를 검토표를 만든다.

  out_real/real_fp_summary.md   사이트별 페이지 수 · 출력 수(기법별) · 페이지당 출력
  out_real/real_fp_review.csv   출력 한 줄씩. verdict 칸에 FP(오탐) / SPAM(진짜 스팸) 을 사람이 적는다
"""
import csv
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "out_real"


def load(p):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def main():
    rows, review = [], []
    for d in sorted(x for x in OUT.iterdir() if x.is_dir()):
        log = load(d / "run_log.json") or {}
        main4 = (load(d / "result.json") or {}).get("findings", [])
        extra = (load(d / "result_extra.json") or {}).get("findings", [])
        pages = log.get("pages", 0)
        tech = Counter(f.get("technique") for f in main4)
        tech_x = Counter(f.get("extra_finding") for f in extra)
        rows.append((d.name, pages, log.get("n_errors", "-"), log.get("elapsed_sec", "-"), len(main4), len(extra),
                     ", ".join(f"{k} {v}" for k, v in tech.most_common()) or "-",
                     ", ".join(f"{k} {v}" for k, v in tech_x.most_common()) or "-",
                     f"{len(main4) / pages:.3f}" if pages else "-"))
        for kind, fs in (("main", main4), ("extra", extra)):
            for f in fs:
                review.append({"site": d.name, "kind": kind, "technique": f.get("extra_finding") or f.get("technique"),
                               "url": f.get("url"), "location": f.get("location"),
                               "evidence_text": str(f.get("evidence_text") or "")[:200].replace("\n", " "),
                               "verdict": ""})
    md = ["# 실제 공공 누리집 오탐 측정", "",
          "| 사이트 | 페이지 | 오류 | 걸린 초 | 4종 출력 | 추가 출력 | 4종 기법별 | 추가 기법별 | 페이지당 4종 출력 |",
          "|---|---:|---:|---:|---:|---:|---|---|---:|"]
    md += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    tp = sum(r[1] for r in rows if isinstance(r[1], int))
    to = sum(r[4] for r in rows)
    md += ["", f"합계: {tp} 페이지, 4종 출력 {to} 건, 추가 출력 {sum(r[5] for r in rows)} 건.",
           "출력은 오탐 후보다. real_fp_review.csv 의 verdict 칸을 채운 뒤 FP 만 세어 오탐률을 낸다."]
    (OUT / "real_fp_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    with (OUT / "real_fp_review.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["site", "kind", "technique", "url", "location", "evidence_text", "verdict"])
        w.writeheader()
        w.writerows(review)
    print("\n".join(md))


if __name__ == "__main__":
    main()
