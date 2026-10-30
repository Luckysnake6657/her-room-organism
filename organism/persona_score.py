# -*- coding: utf-8 -*-
"""盲测计分：输入形如 "1:1 2:2 3:1 ..."，算 B（框架提示词）胜率与 Wilson 区间。"""
import json
import re
import sys


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5)
    return ((c - m) / d, (c + m) / d)


def main():
    raw = sys.argv[1] if len(sys.argv) > 1 else ""
    pairs = dict((int(a), int(b)) for a, b in re.findall(r"(\d+)\s*[:：]\s*(\d+)", raw))
    path = sys.argv[2] if len(sys.argv) > 2 else "evidence/p3/persona_blind.json"
    rows = json.load(open(path, encoding="utf-8"))
    b_win = n = 0
    detail = []
    for i, r in enumerate(rows, 1):
        pick = pairs.get(i)
        if pick not in (1, 2):
            continue
        chosen = r["first"] if pick == 1 else r["second"]
        n += 1
        if chosen[0] == "B":
            b_win += 1
        detail.append(dict(i=i, pick=pick, label=chosen[0], text=chosen[1]))
    lo, hi = wilson(b_win, n)
    out = dict(n=n, b_wins=b_win, rate=round(b_win / n, 3) if n else None,
               ci=[round(lo, 3), round(hi, 3)], detail=detail)
    json.dump(out, open("evidence/p3/persona_blind_score.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps({k: out[k] for k in ("n", "b_wins", "rate", "ci")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
