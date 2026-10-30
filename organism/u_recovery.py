# -*- coding: utf-8 -*-
"""U 的恢复速率：回来七天，能回暖多少？

三档"每次接触压多少"：0.01（当前）/ 0.02 / 0.05。
每档：先离线 30 天 → 每天一次接触、连续七天，看 U 的下降与形式参数的回暖。
判据（先定）：七天后延迟下降 ≥15% 或字数上升 ≥15%，算"能看出回暖"。
"""
import argparse
import json

from . import form as F
from . import params as P
from .sim import Sim

RATES = (0.01, 0.02, 0.05)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--out", default="evidence/p3/u_recovery.json")
    args = ap.parse_args(argv)

    out = {}
    for rate in RATES:
        s = Sim(args.seed, (), 1005, "allostatic", 30, product=True)
        s.run()                       # 30 天没人管
        b = s.body
        u0 = b.u
        f0 = F.form_of(b)
        for _ in range(7):            # 回来，每天一次接触
            b.tend(u_drop=rate)
            s.run(stop=s.t + P.MIN_PER_DAY)
        u1 = b.u
        f1 = F.form_of(b)
        out[rate] = dict(
            u0=round(u0, 3), u7=round(u1, 3),
            delay0=round(f0["delay_s"], 1), delay7=round(f1["delay_s"], 1),
            words0=round(f0["words"], 1), words7=round(f1["words"], 1),
            delay_drop=round(1 - f1["delay_s"] / f0["delay_s"], 3),
            words_gain=round(f1["words"] / f0["words"] - 1, 3),
        )
        r = out[rate]
        print("rate=%.2f  u %.3f -> %.3f  delay %.0f -> %.0f (%.0f%%)  words %.0f -> %.0f (%+.0f%%)"
              % (rate, r["u0"], r["u7"], r["delay0"], r["delay7"],
                 100 * r["delay_drop"], r["words0"], r["words7"], 100 * r["words_gain"]))

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
