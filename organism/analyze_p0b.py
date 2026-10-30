# -*- coding: utf-8 -*-
"""P0b 分析：逐条应激输出边的行为距离 + 与 P0 的可比性检查。"""
import argparse
import json
import os

import numpy as np

from . import params as P
from .run_p0b import EDGES

SD_FLOOR = 0.05


def load(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def dists(idx, cond, seeds, Fb, sd):
    z = (np.array([idx[(cond, s)]["features"] for s in seeds], dtype=float) - Fb) / sd
    return np.sqrt(np.mean(z ** 2, axis=1))


def perm_paired(d_a, d_b, n_perm=5000, seed=0):
    obs = float(d_a.mean() - d_b.mean())
    rs = np.random.default_rng(seed)
    n = len(d_a)
    cnt = 0
    for _ in range(n_perm):
        swap = rs.random(n) < 0.5
        x = np.where(swap, d_b, d_a)
        y = np.where(swap, d_a, d_b)
        if x.mean() - y.mean() >= obs:
            cnt += 1
    return obs, (cnt + 1.0) / (n_perm + 1.0)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="evidence/p0b")
    ap.add_argument("--p0", default="evidence/p0")
    ap.add_argument("--perm", type=int, default=5000)
    args = ap.parse_args(argv)

    recs = load(os.path.join(args.out, "runs.jsonl"))
    idx = {(r["cond"], r["seed"]): r for r in recs}
    seeds = sorted({r["seed"] for r in recs})
    summary = {}

    for suffix, arm in (("_c", "challenge"), ("_d", "dense")):
        Fb = np.array([idx[("base" + suffix, s)]["features"] for s in seeds], dtype=float)
        Fn = np.array([idx[("null" + suffix, s)]["features"] for s in seeds], dtype=float)
        sd = np.maximum(np.std(Fn - Fb, axis=0, ddof=1), SD_FLOOR)
        d_null = dists(idx, "null" + suffix, seeds, Fb, sd)

        print("\n== %s arm ==" % arm)
        print("%-14s %8s %8s %8s %10s %10s" % ("edge", "d", "d_null", "ratio", "p", "p_bonf"))
        rows = {}
        for name, cond in [("all_off", "all_off" + suffix)] + [
                (e, "edge_" + e.replace("stress_", "") + suffix) for e in EDGES]:
            d = dists(idx, cond, seeds, Fb, sd)
            obs, p = perm_paired(d, d_null, args.perm, seed=sum(ord(x) for x in cond))
            rows[name] = dict(d=float(d.mean()), ratio=float(d.mean() / d_null.mean()),
                              p=p, p_bonf=float(min(1.0, p * 6)))
            print("%-14s %8.3f %8.3f %8.2f %10.4f %10.4f" % (
                name, d.mean(), d_null.mean(), d.mean() / d_null.mean(), p, min(1.0, p * 6)))
        summary[arm] = dict(rows=rows, d_null=float(d_null.mean()),
                            survived=float(np.mean([idx[("base" + suffix, s)]["survived"] for s in seeds])))

    # 与 P0 的逐位一致检查（同 seed、同噪声、同世界）
    p0 = {(r["cond"], r["seed"]): r for r in load(os.path.join(args.p0, "runs.jsonl"))}
    diffs = [s for s in seeds if p0[("baseline_c", s)]["features"] != idx[("base_c", s)]["features"]]
    print("\nbase_c vs P0 baseline_c: %d/%d seeds bitwise identical" % (
        len(seeds) - len(diffs), len(seeds)))

    with open(os.path.join(args.out, "summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
