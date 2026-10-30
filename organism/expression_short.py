# -*- coding: utf-8 -*-
"""短版表达：≤10 字，避免因为"话多"吃亏；中性不套模糊句式。"""
import re

CAUSE = re.compile(r"因为|由于|都是你|你害|怪你|所以才")
NEUTRAL = {"平静": "还行吧", "还行": "还行吧", "挺好的": "挺好的",
           "松下来了": "松下来了"}


def render(affect):
    label = str(affect.get("label") or "").strip()
    conf = float(affect.get("confidence") or 0.0)
    comps = affect.get("components") or []
    if not label:
        return "说不上来。"
    if label in NEUTRAL:
        return NEUTRAL[label] + "。"
    if len(comps) >= 2:
        return ("又%s又%s。" % (comps[0], comps[1]))[:12]
    if conf < 0.45:
        line = "说不上来，" + label + "。"
    else:
        line = "我" + label + "。"
    if CAUSE.search(line):
        line = "我" + label + "。"
    return line[:12]
