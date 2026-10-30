# -*- coding: utf-8 -*-
"""事实一致性：嘴可以不说真话，但不能和"她的日子"直接矛盾。

不是禁语检查（那是 claims.py），是**内容 vs 今天的事实**：

- 今天吃过东西 → 不能说"没吃饭/饿着"
- 今天出过门 → 不能说"一直没出门"
- 今天见过人 → 不能说"没人来过"
- 今天没有"不舒服"的事实 → 不强制（她可以说不舒服，那是主观）

冲突时换成一句由事实拼出来的话，不再让模型重写（重写会再编）。
"""
CONFLICTS = (
    ("吃过东西", ("没吃饭", "没怎么吃饭", "饿着", "没吃东西", "一天没吃")),
    ("出过门", ("没出门", "一直没出门", "没出去")),
    ("见过人", ("没人来过", "没人来", "一个人都没见")),
)

# 她的世界里没有这些东西；出现就是把虚构戳破了
WORLD_BANS = ("上班", "公司", "同事", "老板")


def check(text: str, facts, world_bans=None) -> list:
    hits = []
    for fact, bad in CONFLICTS:
        if fact in (facts or []) and any(w in text for w in bad):
            hits.append((fact, [w for w in bad if w in text]))
    for w in (WORLD_BANS if world_bans is None else world_bans):
        if w in text:
            hits.append(("world", [w]))
    return hits


def fallback(facts) -> str:
    parts = [f for f in (facts or []) if f in ("吃过东西", "出过门", "见过人")]
    if not parts:
        return "今天没什么特别的。"
    return "今天" + "，".join(parts) + "。"
