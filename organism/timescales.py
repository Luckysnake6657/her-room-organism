# -*- coding: utf-8 -*-
"""时间尺度实测：每个系统到底有多快。

设计表（`docs/new-direction-organism.md`）说的是七条尺度：秒 / 小时 / 天 / 几小时 /
24 小时 / 几天 / 几个月。这里是**实测**，不是复述常量：

    python -m organism.timescales

做法：把身体放在一个受控环境里，把某个变量推到极端，量它回到阈值要多久。
量出来的不是"参数表上的数"，是**这个模型实际表现出的松弛时间**。
"""
import argparse
import json

from . import params as P
from .model import Body

CTX = dict(hour=8.0, asleep=False, active=False, cold=0.0, light=P.LIGHT_HOME, place=P.HOME)


def _ctx(hour=8.0, light=P.LIGHT_HOME, asleep=False):
    c = dict(CTX)
    c["hour"] = hour
    c["light"] = light
    c["asleep"] = asleep
    return c


def _run_until(body, cond, max_min=200000, ctx=None):
    ctx = ctx or _ctx()
    b = body
    for m in range(max_min):
        if cond(b):
            return m
        b.step(1.0, ctx)
        if b.dead:
            return m
    return max_min


def probe_energy():
    b = Body()
    b.e = 1.0
    t_half = _run_until(b, lambda x: x.e <= 0.5)
    b2 = Body()
    b2.e = 1.0
    t_dead = _run_until(b2, lambda x: x.e <= 0.05)
    return dict(name="能量", designed="小时", half_life_h=t_half / 60.0,
                to_floor_h=t_dead / 60.0, note="从满到半程 / 到饿死线")


def probe_sleep(start_hour):
    b = Body()
    b.s = 0.20
    b.phi = start_hour
    ctx = _ctx(hour=start_hour)
    m = _run_until(b, lambda x: x.s >= 0.90)
    return m / 60.0


def probe_stress():
    b = Body()
    b.a = 0.90
    b.e, b.s, b.l = 0.9, 0.2, 0.12
    target = P.A_BASELINE + (0.90 - P.A_BASELINE) / 2.0
    m = _run_until(b, lambda x: x.a <= target)
    import math
    tau = (m / 60.0) / math.log(2.0)
    return dict(name="应激", designed="几小时（升快、恢复慢）",
                half_life_h=m / 60.0, tau_h=tau, note="从 0.9 回到半程")


def probe_immune():
    b = Body()
    b.i = 0.80
    b.infect = 0.80
    m = _run_until(b, lambda x: x.i <= 0.40)
    return dict(name="免疫/炎症", designed="几天", half_life_h=m / 60.0,
                note="感染后炎症回半程")


def probe_lonely():
    b = Body()
    b.l = 0.12
    m = _run_until(b, lambda x: x.l >= 0.50)
    return dict(name="依恋/孤独", designed="几天 → 几周", to_half_h=m / 60.0,
                note="从设定点到 0.5（无接触）")


def probe_clock():
    # 自由运行：不给光，看内钟相对世界每天漂多少
    b = Body()
    b.phi = 8.0
    start = b.phi
    for _ in range(7 * 24 * 60):
        b.step(1.0, _ctx(hour=(b._hour + 1 / 60.0) % 24 if hasattr(b, "_hour") else 8.0,
                         light=0.0))
    drift_per_day = (b.phi - 8.0 - 7 * 24.0 % 24.0)  # 仅记录，正负不入结论

    # 受牵引：偏 2 小时，看多久拉回 0.5 小时内
    b2 = Body()
    b2.phi = 6.0
    hours = 0
    for m in range(48 * 60):
        hour = (m / 60.0 + 8.0) % 24.0
        b2.step(1.0, _ctx(hour=hour, light=P.LIGHT_OUT))
        hours += 1 / 60.0
        err = abs((b2.phi - hour + 12) % 24 - 12)
        if err <= 0.5:
            break
    return dict(name="昼夜相位", designed="24 小时（自由运行略长）",
                entrain_h=hours, note="偏 2 小时后拉回半小时内")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="evidence/p1/timescales.json")
    args = ap.parse_args(argv)

    rows = [probe_energy(), probe_stress(), probe_immune(), probe_lonely(), probe_clock()]
    sleep_m = probe_sleep(8.0)
    sleep_e = probe_sleep(20.0)
    rows.insert(1, dict(name="睡眠压力", designed="一天",
                        from_morning_h=sleep_m, from_evening_h=sleep_e,
                        note="累积到 0.9 要多久（早八点 / 晚八点起算）"))

    print("%-8s %-22s %s" % ("系统", "设计尺度", "实测"))
    for r in rows:
        vals = ", ".join("%s=%.1f" % (k, v) for k, v in r.items()
                         if k not in ("name", "designed", "note") and isinstance(v, float))
        print("%-8s %-22s %s  (%s)" % (r["name"], r["designed"], vals, r["note"]))

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
