# -*- coding: utf-8 -*-
"""原子化判断：一条记忆是否"谁/什么/何时"的原子事实。"""
import re

TIME_RE = re.compile(r"(今天|明天|昨天|上周|这周|下周|周[一二三四五六日]|\d{1,2}月\d{1,2}日|\d{4}-\d{2}-\d{2})")
ENTITY_RE = re.compile(r"(他|她|我|你|猫|医院|公司|学校|家|茶|药|复查|体检)")


def is_atomic(text: str) -> bool:
    t = str(text or "").strip()
    if len(t) < 4 or len(t) > 60:
        return False
    if t.count("。") > 1 or "\n" in t:
        return False
    return bool(TIME_RE.search(t) or ENTITY_RE.search(t))


def tag(entry: dict) -> dict:
    entry["atomic"] = is_atomic(entry.get("text", ""))
    return entry
