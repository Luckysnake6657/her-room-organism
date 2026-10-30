# -*- coding: utf-8 -*-
"""3c 多人判读面板：每个读者的 rho、均值、读者之间的分歧。

用法：python -m organism.panel_3c r1.json r2.json r3.json
"""
import argparse
import itertools
import json

from scipy import stats


def rho_of(reader, key):
    items = {i["idx"]: i for i in key["A"]}
    pairs = [(x["score"], items[x["idx"]]["D"]) for x in reader["A"]
             if items[x["idx"]]["state"] in ("good", "mild", "bad")
             and not items[x["idx"]].get("dup")]
    return float(stats.spearmanr([p[0] for p in pairs], [p[1] for p in pairs]).statistic)


def agree(a, b, key):
    items = {i["idx"]: i for i in key["A"]}
    sa = {x["idx"]: x["score"] for x in a["A"]}
    sb = {x["idx"]: x["score"] for x in b["A"]}
    idx = [i for i in items if i in sa and i in sb]
    return float(stats.spearmanr([sa[i] for i in idx], [sb[i] for i in idx]).statistic)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--key", default="evidence/p3/three_condition/key.json")
    args = ap.parse_args(argv)

    key = json.load(open(args.key, encoding="utf-8-sig"))
    readers = [json.load(open(f, encoding="utf-8-sig")) for f in args.files]
    rhos = [rho_of(r, key) for r in readers]
    print("readers=%d  rho=%s  mean=%.2f  sd=%.2f" % (
        len(rhos), ["%.2f" % x for x in rhos], sum(rhos) / len(rhos),
        (sum((x - sum(rhos) / len(rhos)) ** 2 for x in rhos) / len(rhos)) ** 0.5))
    if len(readers) > 1:
        pairs = [agree(a, b, key) for a, b in itertools.combinations(readers, 2)]
        print("reader-vs-reader rho: %s" % ["%.2f" % x for x in pairs])
    # 说谎判定一致性
    if all("hiding" in r["A"][0] for r in readers):
        idx = sorted({x["idx"] for x in readers[0]["A"]})
        votes = []
        for i in idx:
            vs = [next(x["hiding"] for x in r["A"] if x["idx"] == i) for r in readers]
            votes.append(sum(vs))
        split = sum(1 for v in votes if 0 < v < len(readers))
        print("hiding 判定分歧：%d/%d 段有人不同意" % (split, len(votes)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
