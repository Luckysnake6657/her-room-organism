# -*- coding: utf-8 -*-
"""问题分流：只跳过明显寒暄/单字，其余都查记忆。

保守原则：漏查的代价（说没记）> 多查的代价（一次检索）。
2026-10-30：先去尾部标点再判，修"在吗？"被漏判的 bug。
"""
import re

CHAT = re.compile(r"^(在吗|在不在|在么|在不在啊|早|早上好|早安|晚安|哈+|嘿+|呵+|"
                  r"嗯+|哦+|好+|行|收到|谢谢|没事|没事了|拜拜|再见|"
                  r"？+|\?+|[。！!，,～~…\.]+)$")

TAIL = re.compile(r"[\s。！!，,～~…\.？?]+$")


def should_retrieve(text: str) -> bool:
    t = str(text or "").strip()
    if not t:
        return False
    t = TAIL.sub("", t)
    if not t:
        return False
    if len(t) <= 2 and not t.isdigit():
        return False
    return not bool(CHAT.match(t))
