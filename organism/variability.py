# -*- coding: utf-8 -*-
"""量化「她的日子有多齐整」：同一个体、不同天之间的时刻抖动。

P0 结果 §六 的第一条局限（"日子太齐整"）需要数字，不然只是感觉。
这里只用行为事件（醒、睡、吃），不碰内部读数。
"""
import argparse
import json
import statistics as st

from . import params as P
from .sim import Sim


def circ_sd(hours):
    if len(hours) < 2:
        return 0.0
    return st.pstdev(hours)


def run_stats(res):
    days = {}
    for e in res["events"]:
        days.setdefault(e["day"], []).append(e)
    wakes, onsets, first_meals, all_meal_days = [], [], [], []
    for d in sorted(days):
        evs = days[d]
        w = [e["hour"] for e in evs if e["kind"] == "wake" and 3.0 <= e["hour"] <= 11.0]
        s = [e["hour"] for e in evs if e["kind"] == "sleep" and e["hour"] >= 17.0]
        m = sorted(e["hour"] for e in evs if e["kind"] == "meal")
        if w:
            wakes.append(min(w))
        if s:
            onsets.append(max(s))
        if m:
            first_meals.append(m[0])
        all_meal_days.append(len(m))
    med = st.median(wakes) if wakes else 0.0
    same = sum(1 for h in wakes if abs(h - med) <= 0.5) / max(1, len(wakes))
    return dict(
        wake_mean=st.mean(wakes) if wakes else 0.0,
        wake_sd=circ_sd(wakes),
        onset_mean=st.mean(onsets) if onsets else 0.0,
        onset_sd=circ_sd(onsets),
        meal_mean=st.mean(first_meals) if first_meals else 0.0,
        meal_sd=circ_sd(first_meals),
        same_within_30min=same,
        meals_per_day=st.mean(all_meal_days) if all_meal_days else 0.0,
        n_days=len(days),
    )


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="0-23")
    ap.add_argument("--out", default="evidence/p0/variability.json")
    ap.add_argument("--challenge", default="")
    args = ap.parse_args(argv)
    seeds = []
    for part in args.seeds.split(","):
        if "-" in part:
            a, b = part.split("-")
            seeds.extend(range(int(a), int(b) + 1))
        else:
            seeds.append(int(part))

    rows = []
    for s in seeds:
        r = Sim(s, (), P.MAIN_NOISE_BASE + s, "allostatic", P.DAYS,
                challenge=bool(args.challenge)).run()
        rows.append(run_stats(r))

    def m(key):
        return st.mean(r[key] for r in rows)

    def sd_of_means(key):
        vals = [r[key] for r in rows]
        return st.pstdev(vals) if len(vals) > 1 else 0.0

    print("within-run SD (hours)   wake=%.2f  onset=%.2f  first_meal=%.2f" % (
        m("wake_sd"), m("onset_sd"), m("meal_sd")))
    print("between-run SD of means wake=%.2f  onset=%.2f  first_meal=%.2f" % (
        sd_of_means("wake_mean"), sd_of_means("onset_mean"), sd_of_means("meal_mean")))
    print("same wake within 30min  %.2f of days" % m("same_within_30min"))
    print("meals per day           %.2f" % m("meals_per_day"))

    out = dict(within=dict(wake=m("wake_sd"), onset=m("onset_sd"), meal=m("meal_sd")),
               between=dict(wake=sd_of_means("wake_mean"),
                            onset=sd_of_means("onset_mean"),
                            meal=sd_of_means("meal_mean")),
               same_within_30min=m("same_within_30min"),
               meals_per_day=m("meals_per_day"),
               per_seed=rows)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
