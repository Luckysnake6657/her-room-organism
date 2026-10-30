# -*- coding: utf-8 -*-
"""结构化行为记录：把「事件流」变成「一天里发生了什么、缺了什么、偏了多少」。

为什么要这一步
--------------
P0 的日志是**边跑边拼出来的句子**：渲染器直接读事件表，句子里的时间词是临时算的。
结果是"半结构化"——有扰动、有碎片、有缺口，但没有锚点、没有环境信号、没有
"这一天和平时比偏了多少"的显式记录。理论方案里的 A/B/E 三个维度就死在这一点上。

这一层只做记录，**不改任何动力学**。它把事件流整理成：

    DayRecord = {
      锚点: 醒来 / 睡下 / 第一顿 / 最后一件出门的事
      事件: 吃、见人（成/没见着）、出门、受惊、跑回、生病
      缺口: 没吃 / 没出门 / 没见人 / 没睡
      环境: 白天多长、傍晚人可能在、天冷
      偏移: 相对本人这七天的中位数，早起/晚起、早睡/晚睡
    }

渲染器再从这些字段写人话——句子跟着记录走，不跟着模板走。
"""
from statistics import median

WAKE_MIN_H, WAKE_MAX_H = 3.0, 12.0
SLEEP_MIN_H = 16.0
SHIFT_WAKE_H = 0.75
SHIFT_SLEEP_H = 1.0
OUT_MIN_FOR_OUTING = 30
SIGNALS = ("dawn", "dusk", "person_arrives", "person_absent", "person_left", "cold_snap")


def _med(vals):
    vals = sorted(v for v in vals if v is not None)
    return median(vals) if vals else None


def _h(ev):
    return float(ev["hour"])


def build_days(res: dict) -> list:
    """从一次运行的结果里整理出逐日记录（不含渲染）。"""
    days = res.get("daily", [])
    events = res.get("events", [])
    out = []
    for d in range(len(days)):
        evs = sorted([e for e in events if e["day"] == d], key=_h)
        rec = dict(day=d, wake=None, sleep=None, meals=[], social=[],
                   outings=[], threats=[], fled=False, sick=0,
                   person_likely=False, day_minutes=0)
        # 醒来：当天第一个"醒"（3–12 点）
        wakes = [e for e in evs if e["kind"] == "wake" and WAKE_MIN_H <= _h(e) <= WAKE_MAX_H]
        if wakes:
            rec["wake"] = _h(wakes[0])
        # 睡下：当天最后一次入睡（优先取午后之后的，白天打盹不算主锚点）
        sleeps = [_h(e) for e in evs if e["kind"] == "sleep"]
        late = [h for h in sleeps if h >= 12.0]
        rec["sleep"] = late[-1] if late else (sleeps[-1] if sleeps else None)
        rec["meals"] = [_h(e) for e in evs if e["kind"] == "meal"]
        for e in evs:
            if e["kind"] == "social":
                rec["social"].append(dict(hour=_h(e), met=True))
            elif e["kind"] == "no_one":
                rec["social"].append(dict(hour=_h(e), met=False))
        rec["threats"] = [_h(e) for e in evs if e["kind"] == "threat"]
        rec["fled"] = any(e["kind"] == "flee" for e in evs)
        rec["signals"] = [dict(kind=e["kind"], hour=_h(e)) for e in evs
                          if e["kind"] in SIGNALS]
        # 出门：按 arrive 的落脚点算起止
        place = None
        start = None
        for e in evs:
            if e["kind"] != "arrive":
                continue
            p = e.get("place")
            if place is None:
                place = 0            # 一天从屋里开始
            if p != 0 and place == 0:
                start = _h(e)
            elif p == 0 and place != 0 and start is not None:
                rec["outings"].append(dict(start=start, end=_h(e)))
                start = None
            place = p
        if start is not None:
            rec["outings"].append(dict(start=start, end=24.0))
        rec["sick"] = int(days[d].get("sick", 0))
        # 原因：只记录"能从前一天/当天更早的事件推出来"的东西
        prev_night = [e for e in events
                      if e["day"] == d - 1 and e["kind"] == "threat" and _h(e) >= 17.0]
        night_threats = [e for e in prev_night] + [h for h in rec["threats"] if h < 6.0]
        rec["night_threats"] = len(night_threats)
        rec["wake_reason"] = ("startled" if night_threats
                              else "sick" if rec["sick"] > 90 else None)
        rec["social_cause"] = ("person_absent"
                               if any(s["kind"] == "person_absent" for s in rec["signals"])
                               else None)
        # 机会过期：今天有人来，但她没去见 —— 窗口自己关了
        arrived = any(s["kind"] == "person_arrives" for s in rec["signals"])
        rec["missed_window"] = bool(arrived and not any(s["met"] for s in rec["social"]))
        rec["person_likely"] = days[d].get("socials", 0) > 0 or any(
            e["kind"] == "no_one" for e in evs)
        rec["day_minutes"] = int(days[d].get("asleep", 0))
        out.append(rec)
    return out


def summarize(res: dict) -> dict:
    """一次运行的七天摘要：中位数、缺口、偏移。"""
    days = build_days(res)
    wake_med = _med([d["wake"] for d in days])
    sleep_med = _med([d["sleep"] for d in days])
    meal_med = _med([d["meals"][0] for d in days if d["meals"]])

    for d in days:
        d["wake_shift"] = (
            None if d["wake"] is None or wake_med is None
            else ("early" if wake_med - d["wake"] >= SHIFT_WAKE_H
                  else "late" if d["wake"] - wake_med >= SHIFT_WAKE_H else "usual"))
        d["sleep_shift"] = (
            None if d["sleep"] is None or sleep_med is None
            else ("early" if sleep_med - d["sleep"] >= SHIFT_SLEEP_H
                  else "late" if d["sleep"] - sleep_med >= SHIFT_SLEEP_H else "usual"))
        d["meal_shift"] = (
            None if not d["meals"] or meal_med is None
            else ("late" if d["meals"][0] - meal_med >= 1.5 else "usual"))
        d["gaps"] = dict(
            no_meal=len(d["meals"]) == 0,
            no_out=sum(o["end"] - o["start"] for o in d["outings"]) * 60 < OUT_MIN_FOR_OUTING,
            no_social=len(d["social"]) == 0,
            no_sleep=(d["sleep"] is None and d["day_minutes"] < 60),
        )
        d["out_hours"] = round(sum(o["end"] - o["start"] for o in d["outings"]), 2)
        d["social_met"] = sum(1 for s in d["social"] if s["met"])
        d["social_missed"] = sum(1 for s in d["social"] if not s["met"])

    return dict(days=days, wake_med=wake_med, sleep_med=sleep_med, meal_med=meal_med)


def validate(summary: dict) -> list:
    """记录层自检：返回问题列表（空 = 通过）。

    不要求每天都有"醒来"锚点：跨日长睡或整天在睡的日子，本来就没有醒来的那一刻。
    只要求每天至少有一个锚点（醒或睡下），或者有明确的缺口记录。
    """
    problems = []
    for d in summary["days"]:
        if d["wake"] is None and d["sleep"] is None and not d["gaps"]["no_sleep"]:
            problems.append("day %d: 既没有醒来也没有睡下锚点" % d["day"])
        if d["meals"] and d["meals"] != sorted(d["meals"]):
            problems.append("day %d: 进食时刻乱序" % d["day"])
        for o in d["outings"]:
            if o["end"] < o["start"]:
                problems.append("day %d: 出门区间倒挂" % d["day"])
    return problems
