# -*- coding: utf-8 -*-
"""表达层（LLM 主、模板兜底）：按披露决定与关系组织语言，守三条硬约束。"""
import re

from . import api_client

CAUSE = re.compile(r"因为|由于|都是你|你害|怪你|所以才")

PROMPT = """你在替她把她此刻的感受说成一句 QQ 消息。
【她的状态分量】%s
【披露决定】%s
【关系】%s
【他刚说】%s
要求：
1. 第一人称、口语、短（≤30 字），不用表情
2. 不许编原因（不写"因为你…""都是你…"）
3. 披露决定是 none 时，**不要提感受**，只回内容
4. 不要每次都一个句式
只输出这一句。"""


def render(affect, context="", relation="owner_private", disclosure=None, model=None):
    mode = (disclosure or affect.get("disclosure") or {}).get("mode", "brief")
    comps = affect.get("components") or []
    body = PROMPT % (
        "、".join(comps) + ("（强度 %.2f）" % float(affect.get("confidence", 0.5))),
        mode, relation, context[:60])
    for _ in range(2):
        try:
            t = api_client.chat(body, context, max_tokens=600, temperature=1.2,
                                model=model).strip()
        except Exception:
            t = ""
        if not t:
            continue
        t = t.replace("\n", " ").strip()[:40]
        if CAUSE.search(t):
            continue
        if mode == "none" and any(c in t for c in comps):
            continue
        return t
    if mode == "none":
        return ""
    from . import expression_short
    return expression_short.render(affect)
