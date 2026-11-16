"""추가 수집 차례마다의 집계: 끝내는 조건을 라벨 초안 기준으로 잰다. 결과는 logs/round_status.csv 에 한 줄씩 덧붙인다.

사용: python round_status.py <차례 이름>
입력: collect/labels_draft.csv(채현 확인 421장) + collect/labels_draft_add.csv(Claude 초안), collect/occurrences_*.csv, collect/images
불법 수는 gate_count.py 와 같이 파일(SHA) 하나를 한 장으로 센다. 사이트 비중은 이미지가 나온 사이트마다 한 번씩 센다.
일반 이미지 = 불법·합법 광고·계도 라벨이 없는 파일(라벨 전 후보 포함). 사이트 종류는 가장 먼저 수집된 기록의 site_type 이다.
배너 = 일반 이미지 중 가로 468px 이상, 가로세로비 2 이상. 가로 468px 이상 전체 수도 같이 적는다.
"""
import csv
import glob
import json
import os
import statistics as st
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import safe_io  # noqa: E402

COL = os.path.join(HERE, "..", "collect")
TYPES = ["news", "shopping", "public", "university", "community", "finance", "hospital"]
NONG = ["loan", "forgery", "drug", "invest", "adult"]


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else "now"
    lab = {}
    for fn in ("labels_draft.csv", "labels_draft_add.csv"):
        p = os.path.join(COL, fn)
        if os.path.exists(p):
            for r in safe_io.read_csv(p):
                lab.setdefault(r["file"], r)
    occ = defaultdict(list)
    for f in glob.glob(os.path.join(COL, "occurrences_*.csv")):
        for r in safe_io.read_csv(f):
            occ[os.path.basename(r["file"])].append(r)
    for v in occ.values():
        v.sort(key=lambda r: r["collected_at"])
    files = [f for f in os.listdir(os.path.join(COL, "images")) if ".tmp" not in f]
    pos = [f for f, r in lab.items() if r["label"] == "illegal"]
    cat = Counter(lab[f]["category"] for f in pos)
    sites = Counter()
    for f in pos:
        for s in {o["site"] for o in occ.get(f, [])}:
            sites[s] += 1
    n = len(pos) or 1
    top = sites.most_common(3)
    print(f"[{name}] 전체 파일 {len(files)}, 라벨 {len(lab)}, 불법 {len(pos)}, 애매 {sum(lab[f]['unsure'] == '1' for f in pos)}")
    print("불법 종류:", dict(cat.most_common()), "| 도박 비중", f"{cat['gambling'] / n:.1%}")
    for c in NONG:
        print(f"  {c}: {cat[c]} (부족 {max(0, 30 - cat[c])})")
    print("불법 출처:", len(sites), "곳, 상위", top, f"1위 {top[0][1] / n:.1%}, 상위 3곳 {sum(v for _, v in top) / n:.1%}" if top else "")
    gen = [f for f in files if lab.get(f, {}).get("label", "other") == "other"]
    by = Counter()
    doms = defaultdict(set)
    for f in gen:
        o = occ.get(f)
        t = o[0]["site_type"] if o else "?"
        by[t] += 1
        doms[t].add(o[0]["site"] if o else "?")
    g = len(gen) or 1
    print("일반 후보", len(gen))
    for t, v in by.most_common():
        mark = "목표종류" if t in TYPES else ""
        print(f"  {t}: {v} ({v / g:.1%}), 도메인 {len(doms[t])} {mark}")
    ok = [t for t in TYPES if by[t] >= 100 and len(doms[t]) >= 5]
    print("100장·5도메인 이상인 목표 종류:", len(ok), ok, "| 가장 큰 종류 비중", f"{by.most_common(1)[0][1] / g:.1%}" if by else "")

    def size(fs, key):
        v = [int(occ[f][0][key]) for f in fs if occ.get(f) and str(occ[f][0][key]).isdigit()]
        return st.median(v) if v else 0
    w468 = [f for f in gen if occ.get(f) and str(occ[f][0]["w"]).isdigit() and int(occ[f][0]["w"]) >= 468]
    banner = [f for f in w468 if int(occ[f][0]["h"] or 1) and int(occ[f][0]["w"]) / max(int(occ[f][0]["h"]), 1) >= 2]
    print(f"크기 중앙값 불법 {size(pos, 'w')}x{size(pos, 'h')}, 일반 {size(gen, 'w')}x{size(gen, 'h')}")
    print(f"일반 가로 468 이상 {len(w468)}, 그중 가로세로비 2 이상 배너 {len(banner)}")
    linked = sum(1 for f in files if occ.get(f) and any(o["page_url"] and o["source_url"] for o in occ[f]))
    print(f"파일 {len(files)} 중 수집 기록(페이지·이미지 주소)과 연결 {linked}, 안 된 것 {len(files) - linked}")
    gam = cat["gambling"] / n
    top1 = top[0][1] / n if top else 1
    top3 = sum(v for _, v in top) / n if top else 1
    big = by.most_common(1)[0][1] / g if by else 1
    table = [
        *[(f"{c} 30장 이상", cat[c] >= 30, cat[c]) for c in NONG],
        ("도박 비중 70% 이하", gam <= 0.70, f"{gam:.1%}"),
        ("한 사이트 10% 이하", top1 <= 0.10, f"{top1:.1%}"),
        ("상위 3곳 합 25% 이하", top3 <= 0.25, f"{top3:.1%}"),
        ("일반 6종 이상(각 100장, 도메인 5곳)", len(ok) >= 6, len(ok)),
        ("일반 한 종류 40% 이하", big <= 0.40, f"{big:.1%}"),
        ("가로 468 이상 배너 200장 이상", len(banner) >= 200, len(banner)),
    ]
    met = all(x[1] for x in table)
    print("달성 기준(라벨 초안 기준):", "모두 달성" if met else "미달")
    for t, o, v in table:
        print(f"  {'달성' if o else '미달'} | {t} | {v}")
    json.dump({"met": met, "round": name, "table": table}, open(os.path.join(HERE, "..", "logs", "criteria.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    row = dict(round=name, files=len(files), illegal=len(pos), gambling_share=f"{cat['gambling'] / n:.3f}",
               top1=f"{top[0][1] / n:.3f}" if top else "", top3=f"{sum(v for _, v in top) / n:.3f}" if top else "",
               **{c: cat[c] for c in NONG}, types_ok=len(ok), biggest_type=f"{by.most_common(1)[0][1] / g:.3f}" if by else "",
               w468=len(w468), banner=len(banner), med_pos=f"{size(pos, 'w')}x{size(pos, 'h')}", med_gen=f"{size(gen, 'w')}x{size(gen, 'h')}")
    p = os.path.join(HERE, "..", "logs", "round_status.csv")
    new = not os.path.exists(p)
    with open(p, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row))
        if new:
            w.writeheader()
        w.writerow(row)


if __name__ == "__main__":
    main()
