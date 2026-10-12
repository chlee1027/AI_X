"""봉인 해제(2026-10-12): 봉인 폴더의 테스트 몫을 저장소로 되돌리고, 10-09~11 새 수집분(DECOY·ETC·조합)을 합친다.

apply_split.py 의 반대 방향이다.
- YAML 샘플: 봉인 쪽 항목 덩어리를 원문 서식 그대로 붙이고 id 순으로 정렬한다. split 칸은 지난 배정 기록으로 남긴다.
- OFFSCREEN 목록 JSON·검수 CSV·메타 dict: 합친다. 화면(fixtures)·보고서 HTML 은 파일째 되돌린다.
- 새 수집분: data/raw/{decoy,etc_new,combo_new}/*_new_20261009.yaml 을 붙인다(split 칸 없음).
  조합에서는 강화군 쏠림 보완으로 뺀 62건(combo_new/ganghwa_keep_drop.yaml 의 drop)을 빼고 data/raw 에 따로 둔다.
- 배정표: 봉인 폴더 split_all.csv 를 data/splits/ 로 옮겨 오고 split_trainval.csv 는 지운다.
봉인 폴더 자체는 건드리지 않는다(복사만). 바꾸기 전 data/ 는 data/raw/backup_before_unseal_20261012/ 에 둔다.

사용: python tools/build/unseal_merge.py 봉인폴더 [--dry]
"""
import csv
import json
import re
import shutil
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from apply_split import SAMPLE_FILES, chunk_id, chunks  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
D = ROOT / "data"
RAW = D / "raw"
BACKUP = RAW / "backup_before_unseal_20261012"
NEW = {"samples/decoy.yaml": RAW / "decoy/decoy_new_20261009.yaml",
       "samples/etc.yaml": RAW / "etc_new/etc_new_20261009.yaml",
       "samples/combo_real.yaml": RAW / "combo_new/combo_new_20261009.yaml"}
DROP = set(yaml.safe_load((RAW / "combo_new/ganghwa_keep_drop.yaml").read_text(encoding="utf-8"))["drop"])
YAMLS = SAMPLE_FILES + ["homoglyph/homoglyph_real_test.yaml", "offscreen/data/samples/offscreen.yaml"]
JSON_LISTS = ["offscreen/data/originals/offscreen_originals.json", "offscreen/data/samples/offscreen.json",
              "offscreen/data/samples/offscreen_controls.json", "offscreen/data/review/fixture_rendering_observations.json",
              "offscreen/data/review/imported_decisions.json"]
META = "offscreen/data/originals/원문근거_수집메타데이터.json"
CSV_REL = "offscreen/data/review/실제광고_국내외_과거포함_검수결과.csv"


def sort_key(i):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", str(i))]


def merge_yaml(rel, seal, dry, log):
    p, q = D / rel, seal / "data" / rel
    head, items = chunks(p.read_text(encoding="utf-8"))
    sealed = chunks(q.read_text(encoding="utf-8"))[1] if q.exists() else []
    new = chunks(NEW[rel].read_text(encoding="utf-8"))[1] if rel in NEW else []
    allc = [c if c.endswith("\n") else c + "\n" for c in items + sealed + new]
    dropped = [c for c in allc if rel == "samples/combo_real.yaml" and chunk_id(c) in DROP]
    allc = [c for c in allc if c not in dropped]
    ids = [chunk_id(c) for c in allc]
    if len(ids) != len(set(ids)):
        sys.exit(f"{rel}: id 중복")
    allc.sort(key=lambda c: sort_key(chunk_id(c)))
    log.append(f"{rel}: 저장소 {len(items)} + 봉인 {len(sealed)} + 새 {len(new)} - 뺌 {len(dropped)} = {len(allc)}")
    if not dry:
        p.write_text(head + "".join(allc), encoding="utf-8", newline="\n")
        if dropped:
            (RAW / "combo_new/ganghwa_dropped_62.yaml").write_text("".join(dropped), encoding="utf-8", newline="\n")


def main(argv):
    seal = Path(argv[0])
    dry = "--dry" in argv
    if not (seal / "split_all.csv").exists():
        sys.exit("봉인 폴더가 아니다")
    if not dry:
        if BACKUP.exists():
            sys.exit(f"백업 폴더가 이미 있다: {BACKUP}")
        shutil.copytree(D, BACKUP, ignore=shutil.ignore_patterns("raw"))
    log = []
    for rel in YAMLS:
        merge_yaml(rel, seal, dry, log)

    for rel in JSON_LISTS:
        p, q = D / rel, seal / "data" / rel
        a = json.loads(p.read_text(encoding="utf-8"))
        b = json.loads(q.read_text(encoding="utf-8")) if q.exists() else []
        m = a + b
        if all("id" in x for x in m):
            m.sort(key=lambda x: sort_key(x["id"]))
        log.append(f"{rel}: {len(a)} + {len(b)} = {len(m)}")
        if not dry:
            p.write_text(json.dumps(m, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")

    p, q = D / META, seal / "data" / META
    a, b = json.loads(p.read_text(encoding="utf-8")), json.loads(q.read_text(encoding="utf-8"))
    if set(a) & set(b):
        sys.exit(f"{META}: 키 겹침")
    log.append(f"{META}: {len(a)} + {len(b)}")
    if not dry:
        p.write_text(json.dumps({**a, **b}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")

    p, q = D / CSV_REL, seal / "data" / CSV_REL
    ra = list(csv.reader(p.read_text(encoding="utf-8-sig").splitlines()))
    rb = list(csv.reader(q.read_text(encoding="utf-8-sig").splitlines()))
    if ra[0] != rb[0]:
        sys.exit(f"{CSV_REL}: 머리줄 다름")
    log.append(f"{CSV_REL}: {len(ra) - 1} + {len(rb) - 1}")
    if not dry:
        with p.open("w", encoding="utf-8-sig", newline="") as f:
            csv.writer(f).writerows(ra + rb[1:])

    files = sorted((seal / "data/offscreen/fixtures").glob("*.html")) + \
        [seal / "data/offscreen/시작.html", seal / "data/offscreen/원문검수_보관.html"]
    for f in files:
        dst = D / f.relative_to(seal / "data")
        if dst.exists():
            sys.exit(f"{dst} 이미 있다")
        if not dry:
            shutil.copy2(f, dst)
    log.append(f"offscreen 화면·보고서 되돌림 {len(files)}")

    if not dry:
        shutil.copy2(seal / "split_all.csv", D / "splits/split_all.csv")
        (D / "splits/split_trainval.csv").unlink()
    log.append("data/splits: split_all.csv 가져옴, split_trainval.csv 지움")
    print("\n".join(log))


if __name__ == "__main__":
    main(sys.argv[1:])
