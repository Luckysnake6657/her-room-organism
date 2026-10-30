# -*- coding: utf-8 -*-
"""P0b：应激的逐边消融。

用法（lab/dc 下）：
    python -m organism.run_p0b --seeds 0-23 --out evidence/p0b
"""
import argparse
import json
import os
import time

from . import params as P
from .sim import Sim

EDGES = ("stress_sleep", "stress_appetite", "stress_avoid",
         "stress_energy", "stress_immune", "stress_social")

ARMS = (("_c", "std"), ("_d", "dense"))


def conditions():
    out = []
    for suffix, challenge in ARMS:
        out.append(("base" + suffix, (), (), challenge))
        out.append(("null" + suffix, (), (), challenge))
        out.append(("all_off" + suffix, ("stress",), (), challenge))
        for e in EDGES:
            out.append((("edge_" + e.replace("stress_", "") + suffix), (), (e,), challenge))
    return out


def parse_seeds(s):
    out = []
    for part in s.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="0-23")
    ap.add_argument("--out", default="evidence/p0b")
    args = ap.parse_args(argv)

    seeds = parse_seeds(args.seeds)
    os.makedirs(args.out, exist_ok=True)
    conds = conditions()

    runs = []
    for name, lesion, edges_off, challenge in conds:
        t0 = time.time()
        noise_base = P.NULL_NOISE_BASE if name.startswith("null") else P.MAIN_NOISE_BASE
        for seed in seeds:
            r = Sim(seed, lesion, noise_base + seed, "allostatic",
                    P.DAYS, challenge=challenge, edges_off=edges_off).run()
            rec = {k: r[k] for k in ("seed", "survived", "days_alive", "death",
                                     "features", "stats", "mean_state", "mean_D",
                                     "daily", "challenge")}
            rec["cond"] = name
            rec["lesion"] = list(lesion)
            rec["edges_off"] = list(edges_off)
            runs.append(rec)
        print("%-18s done (%.1fs)" % (name, time.time() - t0))

    with open(os.path.join(args.out, "runs.jsonl"), "w", encoding="utf-8") as f:
        for rec in runs:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print("wrote %d runs" % len(runs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
