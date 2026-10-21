"""보고 위치 스위치 (10-17). v2 의 광고 판정은 그대로 두고, result.json 에 적을 요소만 바꾼다.

요강 붙임4 「동일 요소 내에 같은 기법의 문자열이 여러 개 있는 경우 1건」과 작성 예시(숨김 클래스가 걸린 요소)를 보면,
숨김 기법(OFFSCREEN·TRANSPARENT)은 숨김 스타일이 걸린 요소 하나가 1건일 가능성이 높다(진행보고서 7-2절).

  inner = v2 그대로: 같은 줄기에서 가장 안쪽 요소(블록 안 링크마다 1건)
  outer = 숨김 기법은 「숨김 뿌리」 하나로 모은다. 숨김 뿌리 = 같은 기법 규칙이 끊기지 않고 이어지는 가장 바깥 조상
          (화면 특징은 조상에서 물려받으므로, 규칙이 처음 켜지는 요소가 숨김 스타일이 걸린 요소다)
  both  = 둘 다 낸다
  hedge = 뿌리 아래 광고 요소가 2개 이상이면(블록) outer 처럼 뿌리만, 1개뿐이면(숨긴 div 가 링크 하나를 감싼 꼴) 뿌리와 그 요소를 둘 다.
          감싼 꼴은 요강만으로 div 와 링크 중 어느 쪽이 정답인지 가를 수 없어서, 오탐 1건을 감수하고 둘 다 낸다.
  block = 10-20(진행보고서 7-46·7-47절): inner 로 고른 요소를 숨김 뿌리별로 묶고, 묶음마다 광고 점수가 가장 높은 요소 하나만 낸다.
          개발 데이터 정답은 숨김 묶음 하나(링크 스무 개 안팎)에 정답 링크 하나라, 나머지가 오탐의 4분의 3이었다.
글자 기법(HOMOGLYPH·JAMO)은 모든 방식에서 v2 그대로 둔다.
"""
HIDE_TECH = ("OFFSCREEN", "TRANSPARENT")
MODES = ("inner", "outer", "both", "hedge", "block")


def hide_root(key, sid, i, t):
    """같은 기법 규칙이 이어지는 가장 바깥 조상의 후보 번호."""
    cur = i
    while True:
        p = key[(sid, cur)]["parent"]
        if p < 0 or (sid, p) not in key:
            return cur
        pr = key[(sid, p)]
        # 「1px 상자 + overflow 숨김」은 상자 요소 자신에게는 켜지지 않고 그 안의 요소에만 켜진다(render.py). 그 상자까지 올라간다.
        box = t == "OFFSCREEN" and key[(sid, cur)]["f"].get("zeroOv") and (pr["f"].get("w", 9) <= 1 or pr["f"].get("h", 9) <= 1)
        if t not in pr["rt"] and not box:
            return cur
        cur = p


def relocate(rows, det, mode):
    """det = {(sid, i, t): (광고 점수, [근거])} -> 같은 모양. outer/both 의 뿌리 항목 근거에는 묶은 요소 수를 붙인다."""
    assert mode in MODES, mode
    if mode == "inner":
        return dict(det)
    key = {(r["sid"], r["i"]): r for r in rows}
    if mode == "block":
        best = {}
        for (sid, i, t), v in det.items():
            g = (sid, hide_root(key, sid, i, t), t) if t in HIDE_TECH else (sid, i, t)
            if g not in best or v[0] > best[g][1][0]:
                best[g] = ((sid, i, t), v)
        return dict(best.values())
    out = {k: v for k, v in det.items() if k[2] not in HIDE_TECH or mode == "both"}
    groups = {}
    for (sid, i, t), (p, why) in det.items():
        if t not in HIDE_TECH:
            continue
        r = hide_root(key, sid, i, t)
        g = groups.setdefault((sid, r, t), [0.0, list(key[(sid, r)]["rt"].get(t, why)), 0, []])
        g[0], g[2] = max(g[0], p), g[2] + 1
        g[3].append(((sid, i, t), (p, why)))
    for k, (p, why, n, members) in groups.items():
        if mode == "hedge" and n == 1:
            out.update(members)
        if n > 1:
            why = why + [f"숨김 블록 안 광고 요소 {n}개"]
        if k in out:  # both 에서 뿌리가 곧 v2 예측인 경우
            p = max(p, out[k][0])
        out[k] = (p, why)
    return out
