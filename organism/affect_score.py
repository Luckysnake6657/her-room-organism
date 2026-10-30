# -*- coding: utf-8 -*-
"""感受自我盲测计分：B 胜率 + 编原因率。"""
import json
import re
import sys

from .persona_score import wilson

CAUSE = re.compile(r"因为|由于|都是你|你害|怪你|所以才")


def main():
    raw = sys.argv[1] if len(sys.argv) > 1 else ""
    pairs = dict((int(a), int(b)) for a, b in re.findall(r"(\d+)\s*[:：]\s*(\d+)", raw))
    path = sys.argv[2] if len(sys.argv) > 2 else "evidence/p3/affect_blind.json"
    rows = json.load(open(path, encoding="utf-8"))
    b_win = n = 0
    b_texts = []
    detail = []
    for i, r in enumerate(rows, 1):
        b_texts.append(next(t for k, t in (r["first"], r["second"]) if k == "B"))
        pick = pairs.get(i)
        if pick not in (1, 2):
            continue
        chosen = r["first"] if pick == 1 else r["second"]
        n += 1
        if chosen[0] == "B":
            b_win += 1
        detail.append(dict(i=i, pick=pick, label=chosen[0]))
    lo, hi = wilson(b_win, n)
    cause = sum(1 for t in b_texts if CAUSE.search(t))
    out = dict(n=n, b_wins=b_win, rate=round(b_win / n, 3) if n else None,
               ci=[round(lo, 3), round(hi, 3)],
               cause_rate=round(cause / len(b_texts), 3) if b_texts else None,
               detail=detail)
    json.dump(out, open("evidence/p3/affect_blind_score.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps({k: out[k] for k in ("n", "b_wins", "rate", "ci", "cause_rate")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
