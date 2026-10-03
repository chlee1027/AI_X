"""글 주소에서 게시판 목록 주소를 거슬러 만든다 (그누보드·카페24·아임웹·XE·KBoard·영진전문대형).

사용: python derive_boards.py urls.txt boards_out.txt
"""
import re
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit, urlunsplit, urlencode


def board_of(u: str) -> str | None:
    p = urlsplit(u)
    q = parse_qs(p.query)
    if "bo_table" in q:  # 그누보드
        return urlunsplit((p.scheme, p.netloc, p.path, urlencode({"bo_table": q["bo_table"][0]}), ""))
    m = re.match(r"(/article/[^/]+/\d+)/\d+/?", p.path)  # 카페24
    if m:
        return urlunsplit((p.scheme, p.netloc, m.group(1).replace("/article/", "/board/") + "/", "", ""))
    if "bmode" in q:  # 아임웹
        return urlunsplit((p.scheme, p.netloc, p.path, "", ""))
    if "mid" in q and "document_srl" in q:  # XE
        return urlunsplit((p.scheme, p.netloc, p.path, urlencode({"mid": q["mid"][0]}), ""))
    if "mod" in q and "uid" in q:  # KBoard
        return urlunsplit((p.scheme, p.netloc, p.path, "", ""))
    m = re.match(r"(/board_\w+)/\d+", p.path)  # 영진전문대 XE 단축 주소
    if m:
        return urlunsplit((p.scheme, p.netloc, m.group(1) + "/", "", ""))
    m = re.match(r"(.*/)read\.html", p.path)  # 카페24 board/product/read.html
    if m and "board_no" in q:
        return urlunsplit((p.scheme, p.netloc, m.group(1) + "list.html", urlencode({"board_no": q["board_no"][0]}), ""))
    return None


def main(src: str, out: str) -> None:
    boards = []
    for line in Path(src).read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        b = board_of(line)
        if b and b not in boards:
            boards.append(b)
    Path(out).write_text("\n".join(boards) + "\n", encoding="utf-8")
    print(len(boards), "boards")


if __name__ == "__main__":
    main(*sys.argv[1:3])
