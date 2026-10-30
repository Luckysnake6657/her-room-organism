# -*- coding: utf-8 -*-
"""照护曲线：一个月没人管之后，回来照顾要多久才缓过来。

三种"照顾强度"（每次见面相当于一次 care）：
    轻  0.3 级/次
    中  0.7 级/次
    重  1.5 级/次

每天照顾一次，量：慢性等级回到 1.0 以下要几天、D 回到 1.2 以下要几天。
这是给"被照顾应该多快缓解"那个问题准备的三条曲线。
"""
import argparse
import json

from . import params as P
from .sim import Sim

STRENGTHS = (("none", 0.0), ("light", 0.3), ("medium", 0.7), ("heavy", 1.5))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--days-alone", type=int, default=30)
    ap.add_argument("--max-days", type=int, default=40)
    ap.add_argument("--out", default="evidence/p1/care_curves.json")
    args = ap.parse_args(argv)

    out = {}
    for name, strength in STRENGTHS:
        sim = Sim(args.seed, (), 1000 + args.seed, "allostatic", args.max_days,
                  product=True)
        body = sim.body
        # 构造"一个月没人管之后"的状态，避免依赖世界长度
        body.chronic = dict(energy=3.0, stress=3.0, immune=3.0)
        body.oor_accum = {k: 3 * 1440.0 for k in body.chronic}
        body.e, body.a, body.i, body.l = 0.32, 0.90, 0.85, 0.90
        body.phi = 8.0
        t0 = sim.t
        start_chronic = dict(body.chronic)
        start_D = body.D()
        curve = [dict(day=0, chronic=round(sum(body.chronic.values()), 2),
                      D=round(body.D(), 2))]
        for day in range(1, args.max_days + 1):
            if strength > 0:
                body.tend(strength)
            sim.run(stop=t0 + day * P.MIN_PER_DAY)
            curve.append(dict(day=day, chronic=round(sum(body.chronic.values()), 2),
                              D=round(body.D(), 2)))
            if sum(body.chronic.values()) < 1.0 and body.D() < 1.2:
                break
        out[name] = dict(strength=strength, start=dict(chronic=start_chronic, D=round(start_D, 2)),
                         curve=curve, recovered_day=curve[-1]["day"],
                         recovered=sum(body.chronic.values()) < 1.0 and body.D() < 1.2)
        print("%-7s strength=%.1f  start D=%.2f chronic=%.1f  ->  day %d recovered=%s" % (
            name, strength, start_D, sum(start_chronic.values()), curve[-1]["day"],
            out[name]["recovered"]))

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
