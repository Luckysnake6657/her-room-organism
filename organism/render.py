# -*- coding: utf-8 -*-
"""把结构化记录渲染成人话：不出现任何数字、单位、变量名。

和 P0 那一版最大的区别：**句子跟着记录走**。
每天先有 record（锚点、事件、缺口、偏移），再决定说什么——
所以"缺了什么"能被说出来（没吃、没出门、没见人），而不是靠人从空白里猜。
"""
import random
import re

from . import record as R

FORBIDDEN = re.compile(r"[0-9]|小时|分钟|秒钟|摄氏度|公斤|厘米|百分之")

SEG = (
    (0, 5, "天还没亮的时候"),
    (5, 8, "清早"),
    (8, 11, "上午"),
    (11, 13, "中午"),
    (13, 17, "下午"),
    (17, 19, "天快黑的时候"),
    (19, 22, "晚上"),
    (22, 24, "夜里"),
)

MEAL = ("去林边吃了点东西", "到林边找了些吃的", "饿了，去林边吃了东西",
        "在林边吃了一阵", "去林边填了肚子")
SOCIAL = ("去门廊跟人坐了一阵", "到门廊那边跟人说了会儿话", "傍晚去门廊见了人",
          "在门廊那边待了会儿")
NO_ONE = ("去门廊等了等，人没来", "去门廊找过人，没见着", "往门廊走了一趟，那边空着")
THREAT = ("在外头被什么惊了一下", "有什么动静，她一下子紧张起来", "外头有响动，她抬了头又低下")
FLEE = ("赶紧躲回屋", "一路跑回了屋", "扭头就往回走")
SICK = ("身上发沉，多半时候待在屋里", "不太舒服，一整天没怎么动", "有点蔫，没怎么出门")
QUIET = ("没什么事，就在屋里待着", "在屋里坐坐站站，没出去")
BUSY = ("在外头耗了大半天", "进进出出好几趟", "一天里出去好几回")


def seg(hour: float) -> str:
    for lo, hi, name in SEG:
        if lo <= hour < hi:
            return name
    return "夜里"


def check_no_numbers(text: str) -> list:
    return [m.group(0) for m in FORBIDDEN.finditer(text)]


def _pick(rng, pool):
    return pool[rng.randrange(len(pool))]


def _wake_phrase(rec, rng):
    if rec["wake"] is None:
        return None
    startled = rec.get("wake_reason") == "startled"
    if rec["wake"] < 5.0:
        return "昨晚被惊动过，天还没亮她就醒了" if startled else "天还没亮她就醒了"
    if rec["wake_shift"] == "early":
        return "昨晚被惊动过，今天醒得比平时早" if startled else "她今天醒得比平时早"
    if rec["wake_shift"] == "late":
        return "昨晚没睡踏实，今天起得比平时晚" if startled else "她今天起得比平时晚"
    return "她%s醒的" % seg(rec["wake"])


def _food_phrase(rec, rng):
    if rec["gaps"]["no_meal"]:
        return "一整天没吃东西"
    if rec["meal_shift"] == "late":
        return "头一顿吃得比平时晚"
    if len(rec["meals"]) >= 4:
        return "吃了好几顿"
    return _pick(rng, MEAL)


def _day_phrase(rec, rng):
    if rec["social_missed"]:
        return _pick(rng, NO_ONE)
    if rec["social_met"]:
        return _pick(rng, SOCIAL)
    if rec["gaps"]["no_out"]:
        return _pick(rng, QUIET)
    if rec["out_hours"] >= 7:
        return _pick(rng, BUSY)
    return "出门转了一阵"


def _night_phrase(rec, rng, daily):
    bouts = int(daily.get("bouts", 0)) if daily else 0
    if rec["gaps"]["no_sleep"]:
        return "整夜没合眼"
    if rec["sleep_shift"] == "late":
        return "熬到很晚才睡"
    if rec["sleep_shift"] == "early":
        return "今天早早就困了"
    if bouts > 1:
        return "夜里醒了又睡，睡了又醒"
    return "一觉睡到天亮"


def render_day(res, day, rng, summary=None):
    summary = summary or R.summarize(res)
    rec = summary["days"][day]
    parts = []

    w = _wake_phrase(rec, rng)
    if w:
        parts.append(w)
    parts.append(_food_phrase(rec, rng))
    parts.append(_day_phrase(rec, rng))
    if rec["threats"]:
        parts.append(_pick(rng, THREAT))
        if rec["fled"]:
            parts.append(_pick(rng, FLEE))
    if rec["sick"] > 90:
        parts.append(_pick(rng, SICK))

    # 睡觉那句放最后
    parts.append(_night_phrase(rec, rng, res["daily"][day] if day < len(res["daily"]) else None))

    # 去重 + 截断（保留最后一句"夜里……"）
    seen = []
    for p in parts:
        if p not in seen:
            seen.append(p)
    body, night = seen[:-1], seen[-1]
    body = body[:4]
    sep = "；" if rng.random() < 0.25 else "，"
    return sep.join(body + [night]) + "。"


def render_run(res, seed, max_days=None):
    summary = R.summarize(res)
    n = len(summary["days"]) if max_days is None else min(max_days, len(summary["days"]))
    rng = random.Random(seed * 7919 + 13)
    lines = []
    for d in range(n):
        if d > 0:
            lines.append("")
        lines.append(render_day(res, d, rng, summary))
    if res.get("death"):
        lines.append("")
        lines.append("后来有一天，她没再醒过来。")
    return "\n".join(lines)
