# -*- coding: utf-8 -*-
"""跑 P0：条件 × 种子，写 runs.jsonl 与逐日文本。

用法（在 lab/dc 下）：
    python -m organism.run_p0 --seeds 90-99 --out evidence/p0_dev
    python -m organism.run_p0 --seeds 0-23  --out evidence/p0
"""
import argparse
import json
import os
import time

from . import params as P
from .render import check_no_numbers, render_run
from .sim import Sim

BASE_CONDITIONS = (
    # name, lesion, policy mode, noise base
    ("baseline", (), "allostatic", P.MAIN_NOISE_BASE),
    ("null", (), "allostatic", P.NULL_NOISE_BASE),
    ("cosmetic", ("dummy",), "allostatic", P.MAIN_NOISE_BASE),
    ("shuffle", (), "shuffle", P.MAIN_NOISE_BASE),
    ("lesion_energy", ("energy",), "allostatic", P.MAIN_NOISE_BASE),
    ("lesion_sleep", ("sleep",), "allostatic", P.MAIN_NOISE_BASE),
    ("lesion_stress", ("stress",), "allostatic", P.MAIN_NOISE_BASE),
    ("lesion_immune", ("immune",), "allostatic", P.MAIN_NOISE_BASE),
    ("lesion_lonely", ("lonely",), "allostatic", P.MAIN_NOISE_BASE),
    ("lesion_clock", ("clock",), "allostatic", P.MAIN_NOISE_BASE),
)


def _conditions():
    out = []
    for suffix, challenge in (("", False), ("_c", True)):
        for name, lesion, mode, noise in BASE_CONDITIONS:
            out.append((name + suffix, lesion, mode, noise, challenge))
    return tuple(out)


CONDITIONS = _conditions()

LESIONS = [c[0] for c in BASE_CONDITIONS if c[0].startswith("lesion_")]


def parse_seeds(s: str):
    out = []
    for part in s.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


def run(seed: int, cond):
    name, lesion, mode, noise_base, challenge = cond
    t0 = time.time()
    sim = Sim(seed, lesion, noise_base + seed, mode, P.DAYS, challenge=challenge)
    res = sim.run()
    rec = {k: res[k] for k in (
        "seed", "lesion", "mode", "challenge", "survived", "days_alive", "death",
        "death_day", "features", "stats", "mean_state", "lonely_max",
        "mean_D", "daily")}
    rec["cond"] = name
    rec["noise_seed"] = noise_base + seed
    rec["events"] = res["events"]
    rec["elapsed_s"] = round(time.time() - t0, 3)
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="0-23")
    ap.add_argument("--out", default="evidence/p0")
    ap.add_argument("--render-days", type=int, default=3)
    ap.add_argument("--render-seeds", default="0-2")
    args = ap.parse_args(argv)

    seeds = parse_seeds(args.seeds)
    os.makedirs(args.out, exist_ok=True)
    os.makedirs(os.path.join(args.out, "transcripts"), exist_ok=True)

    runs = []
    for cond in CONDITIONS:
        for seed in seeds:
            rec = run(seed, cond)
            runs.append(rec)
            if seed % 6 == 0:
                print("[%s %d] surv=%s days=%.2f meals=%.0f death=%s" % (
                    cond[0], seed, rec["survived"], rec["days_alive"],
                    rec["stats"]["meals"], rec["death"] or "-"))

    with open(os.path.join(args.out, "runs.jsonl"), "w", encoding="utf-8") as f:
        for rec in runs:
            slim = {k: v for k, v in rec.items() if k != "events"}
            f.write(json.dumps(slim, ensure_ascii=False) + "\n")

    # 逐日文本（基线 + 每个消融各挑几个种子）
    render_seeds = parse_seeds(args.render_seeds)
    bad = 0
    for rec in runs:
        if rec["seed"] not in render_seeds:
            continue
        if rec["cond"] not in (("baseline", "baseline_c") + tuple(LESIONS)
                               + tuple(l + "_c" for l in LESIONS)
                               + ("shuffle", "cosmetic", "shuffle_c", "cosmetic_c")):
            continue
        text = render_run(rec, rec["seed"], args.render_days)
        hits = check_no_numbers(text)
        if hits:
            bad += 1
            print("WARN digits/units in %s s%d: %s" % (rec["cond"], rec["seed"], hits[:5]))
        path = os.path.join(args.out, "transcripts",
                            "%s_s%02d.txt" % (rec["cond"], rec["seed"]))
        with open(path, "w", encoding="utf-8") as f:
            f.write(text + "\n")

    print("wrote %d runs to %s (no-number violations: %d)" % (len(runs), args.out, bad))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
