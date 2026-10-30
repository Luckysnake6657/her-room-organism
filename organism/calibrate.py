# -*- coding: utf-8 -*-
"""标定用：在开发种子上跑一遍，看基线行为是否像「过日子」。

只打印 ASCII，避免 GBK 控制台。
"""
import sys

from . import params as P
from .sim import Sim


def main(argv):
    seeds = [int(x) for x in argv[1].split(",")] if len(argv) > 1 else list(P.DEV_SEEDS)
    days = int(argv[2]) if len(argv) > 2 else P.DAYS
    print("seed surv days meals/d sleep_h/d bouts/d social/d out_h/d sick_h/d meanD  e     s     a     i     l    lmax  m")
    for sd in seeds:
        r = Sim(sd, (), P.MAIN_NOISE_BASE + sd, "allostatic", days).run()
        st = r["stats"]
        ms = r["mean_state"]
        d = max(1e-6, r["days_alive"])
        print("%4d %4s %5.2f %7.2f %8.2f %7.2f %7.2f %6.2f %8.2f %5.2f %5.2f %5.2f %5.2f %5.2f %5.2f %5.2f %4.2f %s" % (
            sd, r["survived"], r["days_alive"], st["meals"] / d,
            st["asleep"] / 60.0 / d, st["bouts"] / d, st["socials"] / d,
            st["out"] / 60.0 / d, st["sick"] / 60.0 / d, r["mean_D"],
            ms["e"], ms["s"], ms["a"], ms["i"], ms["l"], r["lonely_max"], ms["m"],
            r["death"] or "-"))


if __name__ == "__main__":
    main(sys.argv)
