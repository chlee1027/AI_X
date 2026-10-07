"""make_split.py 배정대로 테스트 몫을 저장소 밖(봉인 폴더)으로 옮기고, 저장소 파일에는 학습·검증만 남긴다.

- YAML 샘플 파일은 항목 경계(줄 처음의 `- `)로 잘라 옮긴다. 원래 서식을 그대로 두고 항목마다 `split: train|val` 줄만 넣는다
  (사람 2 HOMOGLYPH 처럼 split 칸이 이미 있으면 값만 바꾼다).
- OFFSCREEN 시험용(파생) 100 과 그 화면(fixtures/OF-xxx.html)은 같은 광고 문구의 원문을 따른다.
- OFFSCREEN 검수 기록 가운데 테스트 문구가 든 것: 목록형 JSON·CSV 는 해당 항목만 옮기고,
  보고서 HTML(시작.html·원문검수_보관.html)은 파일째 봉인 폴더로 옮긴다.
- HOMOGLYPH 전체판에서 테스트 묶음의 행(권장판 테스트 + 전체판에만 있는 같은 묶음 행)은 봉인 폴더로 옮긴다.
- 배정표: 저장소에는 학습·검증만(data/splits/split_trainval.csv), 테스트까지 든 전체 배정표는 봉인 폴더에.

사용: python tools/build/apply_split.py 봉인폴더 [--dry]
"""
import csv
import json
import re
import shutil
import sys
from collections import Counter
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_split import assign, gather, report  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data"
OFF = D / "offscreen"
SAMPLE_FILES = ["samples/decoy.yaml", "samples/etc.yaml", "samples/combo_real.yaml", "samples/jamo.yaml",
                "offscreen/data/originals/offscreen_originals.yaml", "homoglyph/homoglyph_real_test_capped.yaml"]


def chunks(text):
    """YAML 목록을 항목 원문 덩어리로 자른다. 첫 덩어리 앞의 머리말은 따로 돌려준다."""
    parts = re.split(r"(?m)^(?=- )", text)
    head, items = (parts[0], parts[1:]) if not parts[0].startswith("- ") else ("", parts)
    return head, items


def with_split(chunk, split):
    if re.search(r"(?m)^  split: ", chunk):
        return re.sub(r"(?m)^  split: .*$", f"  split: {split}", chunk, count=1)
    first, _, rest = chunk.partition("\n")
    return f"{first}\n  split: {split}\n{rest}"


def chunk_id(chunk):
    return yaml.safe_load(chunk)[0]["id"]


def split_yaml(rel, split_of, seal, dry, default=None):
    """split_of(id) -> train|val|test|None(None 이면 default)."""
    p = D / rel
    head, items = chunks(p.read_text(encoding="utf-8"))
    keep, out = [], []
    cnt = Counter()
    for c in items:
        s = split_of(chunk_id(c)) or default
        cnt[s] += 1
        if s == "test":
            out.append(c)
        else:
            keep.append(with_split(c, s) if s in ("train", "val") else c)
    if not dry:
        p.write_text(head + "".join(keep), encoding="utf-8", newline="\n")
        if out:
            q = seal / "data" / rel
            q.parent.mkdir(parents=True, exist_ok=True)
            q.write_text(head + "".join(with_split(c, "test") for c in out), encoding="utf-8", newline="\n")
    return cnt


def split_json_list(rel, is_test, seal, dry, indent=1):
    p = D / rel
    data = json.loads(p.read_text(encoding="utf-8"))
    keep = [x for x in data if not is_test(x)]
    out = [x for x in data if is_test(x)]
    if not dry and out:
        p.write_text(json.dumps(keep, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8", newline="\n")
        q = seal / "data" / rel
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_text(json.dumps(out, ensure_ascii=False, indent=indent) + "\n", encoding="utf-8", newline="\n")
    return len(keep), len(out)


def move(rel, seal, dry):
    p = D / rel
    if p.exists() and not dry:
        q = seal / "data" / rel
        q.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(p), str(q))
    return p.exists() or dry


def main(argv):
    seal = Path(argv[0])
    dry = "--dry" in argv
    out, forced, gcat = assign(gather())
    sp = {k: v["split"] for k, v in out.items()}
    norm = lambda t: re.sub(r"\s+", "", str(t))  # noqa: E731

    log = []
    # 1) 샘플 YAML
    for rel in SAMPLE_FILES:
        log.append(f"{rel} {dict(split_yaml(rel, sp.get, seal, dry))}")

    # 2) HOMOGLYPH 전체판: 테스트 묶음 행을 옮긴다. 권장판에도 있는 행은 권장판 배정, 나머지는 묶음 배정을 따른다
    def full_split(i):
        s = sp.get(i)
        return {"test_campaign_extra": "test", "val_campaign_extra": "val"}.get(s, s)
    log.append(f"homoglyph/homoglyph_real_test.yaml {dict(split_yaml('homoglyph/homoglyph_real_test.yaml', full_split, seal, dry))}")
    for rel in ("homoglyph/add/add_cyrillic.yaml", "homoglyph/add/add_cyrillic_2_owncorpus.yaml"):
        log.append(f"{rel} {dict(split_yaml(rel, full_split, seal, dry, default='train'))}")

    # 3) OFFSCREEN 파생·검수 기록
    orig = yaml.safe_load((OFF / "data/originals/offscreen_originals.yaml").read_text(encoding="utf-8")) if dry else None
    if orig is None:  # 원문 파일은 1) 에서 이미 나뉘었으니 봉인 쪽까지 합쳐 읽는다
        orig = yaml.safe_load((OFF / "data/originals/offscreen_originals.yaml").read_text(encoding="utf-8")) or []
        sealed = seal / "data/offscreen/data/originals/offscreen_originals.yaml"
        if sealed.exists():
            orig += yaml.safe_load(sealed.read_text(encoding="utf-8")) or []
    test_ev = {norm(o["evidence_text"]) for o in orig if sp[o["id"]] == "test"}
    test_ids = {o["id"] for o in orig if sp[o["id"]] == "test"}
    ev_split = {}
    for o in orig:
        ev_split.setdefault(norm(o["evidence_text"]), set()).add(sp[o["id"]])
    src_split = {}
    for o in orig:
        src_split.setdefault(o["source"], set()).add(sp[o["id"]])
    clash = {e: s for e, s in ev_split.items() if len(s) > 1}
    if clash:
        sys.exit(f"같은 문구가 여러 몫에 걸침(make_split 의 ev 묶음이 안 됨): {list(clash)[:3]}")

    def derived_split(x):
        s = ev_split.get(norm(x["evidence_text"])) or src_split.get(x["source"])
        if not s or len(s) > 1:
            sys.exit(f"{x['id']}: 원문을 못 찾거나 여러 몫에 걸침 {s}")
        return next(iter(s))

    der = yaml.safe_load((OFF / "data/samples/offscreen.yaml").read_text(encoding="utf-8"))
    der_split = {x["id"]: derived_split(x) for x in der}
    ctrl = json.loads((OFF / "data/samples/offscreen_controls.json").read_text(encoding="utf-8"))
    ctrl_split = {x["id"]: derived_split(x) for x in ctrl}
    log.append(f"offscreen/data/samples/offscreen.yaml {dict(split_yaml('offscreen/data/samples/offscreen.yaml', der_split.get, seal, dry))}")
    der_test = {i for i, s in der_split.items() if s == "test"}
    ctrl_test = {i for i, s in ctrl_split.items() if s == "test"}
    all_test_ids = test_ids | der_test | ctrl_test
    is_test_item = lambda x: x.get("id") in all_test_ids or norm(x.get("evidence_text", "")) in test_ev  # noqa: E731
    for rel in ("offscreen/data/originals/offscreen_originals.json", "offscreen/data/samples/offscreen.json",
                "offscreen/data/samples/offscreen_controls.json", "offscreen/data/review/fixture_rendering_observations.json",
                "offscreen/data/review/imported_decisions.json"):
        log.append(f"{rel} 남김·옮김 {split_json_list(rel, is_test_item, seal, dry)}")
    # 원문근거 메타: 키별 dict. 값에 테스트 문구·id 가 들면 옮긴다
    meta_rel = "offscreen/data/originals/원문근거_수집메타데이터.json"
    meta = json.loads((D / meta_rel).read_text(encoding="utf-8"))
    test_src = {o["source"] for o in orig if sp[o["id"]] == "test"}
    hit = lambda v: any(e and e in norm(json.dumps(v, ensure_ascii=False)) for e in test_ev) or \
        any(u in json.dumps(v, ensure_ascii=False) for u in test_src) or \
        any(re.search(re.escape(i) + r"\b", json.dumps(v, ensure_ascii=False)) for i in all_test_ids)  # noqa: E731
    mk = {k: v for k, v in meta.items() if not hit(v)}
    mo = {k: v for k, v in meta.items() if hit(v)}
    if not dry and mo:
        (D / meta_rel).write_text(json.dumps(mk, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
        q = seal / "data" / meta_rel
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_text(json.dumps(mo, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    log.append(f"{meta_rel} 남김·옮김 {(len(mk), len(mo))}")
    # 검수 CSV: 테스트 문구가 든 행을 옮긴다
    csv_rel = "offscreen/data/review/실제광고_국내외_과거포함_검수결과.csv"
    rows = list(csv.reader((D / csv_rel).read_text(encoding="utf-8-sig").splitlines()))
    ck = [rows[0]] + [r for r in rows[1:] if not any(e and e in norm("".join(r)) for e in test_ev)]
    co = [rows[0]] + [r for r in rows[1:] if any(e and e in norm("".join(r)) for e in test_ev)]
    if not dry and len(co) > 1:
        for dst, rs in ((D / csv_rel, ck), (seal / "data" / csv_rel, co)):
            dst.parent.mkdir(parents=True, exist_ok=True)
            with dst.open("w", encoding="utf-8-sig", newline="") as f:
                csv.writer(f).writerows(rs)
    log.append(f"{csv_rel} 남김·옮김 {(len(ck) - 1, len(co) - 1)}")
    # 화면(fixtures): 테스트 파생·대조군 id 의 파일과, 테스트 문구가 든 파일
    moved_fx = []
    for fx in sorted((OFF / "fixtures").glob("*.html")):
        t = norm(fx.read_text(encoding="utf-8", errors="replace"))
        if fx.stem in all_test_ids:
            moved_fx.append(fx.stem)
            move(f"offscreen/fixtures/{fx.name}", seal, dry)
        elif any(e and e in t for e in test_ev):
            sys.exit(f"{fx.name}: 학습·검증 화면에 테스트 문구가 들어 있다(묶음이 덜 이어짐)")
    log.append(f"offscreen/fixtures 옮김 {len(moved_fx)} {moved_fx}")
    for rel in ("offscreen/시작.html", "offscreen/원문검수_보관.html"):
        move(rel, seal, dry)
        log.append(f"{rel} 파일째 옮김")

    # 4) 배정표
    rows = [(k, v["category"], v["subtype"], v["split"]) for k, v in sorted(out.items())]
    rows += [(i, "OFFSCREEN_DERIVED", "", s) for i, s in sorted(der_split.items())]
    rows += [(i, "OFFSCREEN_CONTROL", "", s) for i, s in sorted(ctrl_split.items())]
    if not dry:
        (D / "splits").mkdir(exist_ok=True)
        with (D / "splits/split_trainval.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "category", "subtype", "split"])
            w.writerows(r for r in rows if r[3] in ("train", "val", "val_campaign_extra"))
        with (seal / "split_all.csv").open("w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "category", "subtype", "split"])
            w.writerows(rows)
        (seal / "split_report.txt").write_text(report(out, forced, gcat) + "\n\n" + "\n".join(log) + "\n", encoding="utf-8")
    print("\n".join(log))


if __name__ == "__main__":
    main(sys.argv[1:])
