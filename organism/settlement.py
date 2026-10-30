# -*- coding: utf-8 -*-
"""结算单：只讲世界里发生了什么，不讲"她因为你而怎样"。

三条硬规则（2026-10-27，来自反方评审）：
1. **主语是世界/时间，不是她，也不是你**："独处了几天""窗口关了"，
   不是"你不在的那几天"，也不是"她的状态从多少变到多少"。
2. **不做反事实对比**：不出现"如果你在""本来会怎样"。
3. **单次结算、不跨期累计**：这一次离开的账在这一次结完，不滚进下一次。

判据：不出现第二人称、不出现"如果/本来/上次/又"、不出现 ASCII 数字、
不触发 claims 的越界词。这个函数只能被**显式调用**（用户主动查），不推送。
"""
import re

from . import claims

CN = "零一二三四五六七八九"


def cn_num(n: int) -> str:
    n = int(n)
    if n == 2:
        return "两"          # 两 天 / 两 次 / 两 顿
    if n < 10:
        return CN[n]
    if n < 20:
        return "十" + (CN[n % 10] if n % 10 else "")
    if n < 100:
        return CN[n // 10] + "十" + (CN[n % 10] if n % 10 else "")
    return "很多"


FORBIDDEN = ("你", "如果", "本来", "又", "上次")


def text_for(gap: dict) -> str:
    days = gap.get("days_alone", 0.0)
    meals = int(gap.get("meals", 0))
    missed = int(gap.get("missed_windows", 0))
    sick_h = gap.get("sick_minutes", 0) / 60.0

    parts = []
    if days >= 1:
        parts.append("独处了" + cn_num(round(days)) + "天")
    if missed:
        parts.append("有" + cn_num(missed) + "次见面窗口到了就关了")
    if meals:
        parts.append("吃了" + cn_num(meals) + "顿")
    if sick_h >= 1:
        parts.append("身体不适约" + cn_num(round(sick_h)) + "个钟头")
    if not parts:
        parts.append("没有特别的事")
    text = "这段时间：" + "，".join(parts) + "。"

    bad = [w for w in FORBIDDEN if w in text]
    if bad:
        raise ValueError("结算单越界（第二人称/反事实/累计）: %s" % bad)
    if re.search(r"[0-9]", text):
        raise ValueError("结算单里出现了阿拉伯数字")
    if claims.check_claims(text):
        raise ValueError("结算单越界: %s" % claims.check_claims(text))
    return text
