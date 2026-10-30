# -*- coding: utf-8 -*-
"""开发用：把轨迹打成 ASCII，避免 GBK 控制台炸掉。

用法：
    python -m organism.trace [seed] [noise_seed] [days]
"""
import sys

from . import params as P
from .model import circ_dist_h
from .sim import Sim


def main(argv):
    seed = int(argv[1]) if len(argv) > 1 else P.DEV_SEEDS[0]
    noise = int(argv[2]) if len(argv) > 2 else P.MAIN_NOISE_BASE + seed
    days = int(argv[3]) if len(argv) > 3 else P.DAYS
    sim = Sim(seed, (), noise, "allostatic", days)
    res = sim.run()

    for r in sim.trace[::2]:
        print("d%d %05.1f p%d %-6s e=%.2f s=%.2f a=%.2f i=%.2f l=%.2f phi=%05.2f m=%.2f D=%.2f" % (
            r["day"], r["hour"], r["place"], r["kind"], r["e"], r["s"], r["a"],
            r["i"], r["l"], r["phi"], circ_dist_h(r["phi"], r["hour"]), r["D"]))
    print("RESULT survived=%s days=%.2f death=%s meals=%.1f sleep_h=%.1f socials=%.1f out_h=%.1f flees=%d threats=%d" % (
        res["survived"], res["days_alive"], res["death"],
        res["stats"]["meals"], res["stats"]["asleep"] / 60.0,
        res["stats"]["socials"], res["stats"]["out"] / 60.0,
        res["stats"]["flees"], res["stats"]["threats"]))


if __name__ == "__main__":
    main(sys.argv)
