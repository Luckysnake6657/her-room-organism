import glob
import json
import math


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - h) / d, (c + h) / d


for t in (3, 10):
    key = {str(k["i"]): k["ours_side"]
           for k in json.load(open("evidence/p3/shadow_c%d/key.json" % t, encoding="utf-8-sig"))}
    rates, total, n = [], 0, 0
    for f in sorted(glob.glob("evidence/p3/shadow_c%d/rater_*.json" % t)):
        r = json.load(open(f, encoding="utf-8-sig"))
        w = sum(1 for i, s in key.items() if r.get(i) == s)
        tie = sum(1 for i, s in key.items() if r.get(i) == "平")
        rates.append((w + tie) / 20)
        total += w + tie
        n += 20
    lo, hi = wilson(total, n)
    print("turns", t, "raters", [round(x, 2) for x in rates],
          "mean", round(sum(rates) / len(rates), 2),
          "pooled", round(total / n, 2), "CI", (round(lo, 2), round(hi, 2)))
