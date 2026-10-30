# -*- coding: utf-8 -*-
"""表达层（确定性版）：把感受推断说成第一人称的一句话。

规则：第一人称、允许模糊、不编原因、不说"系统显示"。
LLM 版本只在切换后使用；这里保证底线不破。
"""
import re

CAUSE = re.compile(r"因为|由于|都是你|你害|怪你|所以才")
NATURAL = {"就那样", "还行吧", "挺好的", "松下来了"}


def render(affect):
    phrase = str(affect.get("phrase") or "").strip()
    want = str(affect.get("want") or "").strip()
    conf = float(affect.get("confidence") or 0.0)
    if not phrase:
        return ""
    if phrase in NATURAL:
        return phrase + "。"
    line = "我现在" + phrase + "。"
    # 置信够高才说想要什么；低置信不替她下结论
    if conf >= 0.6 and want and "不想被打扰" not in want:
        line += want + "。"
    if CAUSE.search(line):
        # 绝不带无依据因果；退回只说状态
        line = "我现在" + phrase + "。"
    return line
