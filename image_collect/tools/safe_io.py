"""일시 정지·전원 차단에 견디는 기록 읽기·이어 쓰기.

PAUSE: collect/PAUSE 가 있으면 수집·OCR 은 진행 중인 항목만 마치고 끝난다.
repair_tail: 이어 쓰기 전에 끝이 잘린 줄을 찾아 logs/truncated_tails.log 로 옮기고 그 앞까지로 파일을 자른다.
  따옴표 안의 줄바꿈은 줄 끝으로 치지 않는다. 온전한 기록은 건드리지 않는다.
read_csv: NUL 바이트와 칸 수가 맞지 않는 줄(다른 프로세스가 쓰는 중이거나 잘린 줄)을 건너뛰고 읽는다.
"""
import csv
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
PAUSE = os.path.join(ROOT, "collect", "PAUSE")
csv.field_size_limit(10_000_000)


def paused():
    return os.path.exists(PAUSE)


def repair_tail(path, quoted=True):
    """잘린 끝줄을 옮겨 적고 파일을 온전한 마지막 줄까지로 자른다. 옮긴 바이트 수를 돌려준다."""
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return 0
    with open(path, "rb") as f:
        data = f.read()
    end = 0
    in_q = False
    for i, b in enumerate(data):
        if b == 0x22 and quoted:  # "
            in_q = not in_q
        elif b == 0x0A and not in_q:
            end = i + 1
    if end == len(data):
        return 0
    tail = data[end:]
    with open(os.path.join(ROOT, "logs", "truncated_tails.log"), "ab") as f:
        f.write(os.path.basename(path).encode() + b"\t" + tail.replace(b"\x00", b"") + b"\n")
    with open(path, "r+b") as f:
        f.truncate(end)
    return len(tail)


def read_csv(path):
    """온전한 줄만 dict 로 돌려준다."""
    if not os.path.exists(path):
        return []
    with open(path, "rb") as f:
        text = f.read().replace(b"\x00", b"").decode("utf-8", "replace")
    rows = []
    rd = csv.reader(io.StringIO(text, newline=""))
    try:
        head = next(rd)
    except StopIteration:
        return []
    for vals in rd:
        if len(vals) == len(head):
            rows.append(dict(zip(head, vals)))
    return rows


def read_jsonl(path):
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, "rb") as f:
        for line in f.read().replace(b"\x00", b"").split(b"\n"):
            if line.strip():
                try:
                    rows.append(json.loads(line.decode("utf-8", "replace")))
                except ValueError:
                    pass
    return rows
