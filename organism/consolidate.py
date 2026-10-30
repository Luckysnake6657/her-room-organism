# -*- coding: utf-8 -*-
"""巩固：把最近重复出现的情景，压成一条候选语义记忆。

铁律：**候选文本必须逐字来自已有条目**，不能改写、不能总结。巩固只做"挑出来"，
不做"写出来"。挑出来的进 pending，等用户确认。

这是睡眠里发生的事的最小版本：不是压缩，是"这事反复出现，值得单独记一笔"。
"""
import datetime as dt

from . import habits


def _age_days(created_at: str, now: dt.datetime) -> float:
    try:
        t = dt.datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S")
    except Exception:
        return 999.0
    return max(0.0, (now - t).total_seconds() / 86400.0)


def candidates(nb, now=None, days: int = 7, min_count: int = 3):
    now = now or dt.datetime.now()
    recent = []
    for e in nb.live():
        if e["status"] == "pending":
            continue
        if _age_days(e["created_at"], now) <= days:
            recent.append(e)

    topic_entries = {}
    for e in recent:
        text = e["text"]
        grams = {text[i:i + 2] for i in range(max(0, len(text) - 1))}
        grams = {g for g in grams if g not in habits.STOP and not g.startswith(("你", "我"))}
        for g in grams:
            topic_entries.setdefault(g, []).append(e)

    out, seen = [], set()
    for topic, entries in sorted(topic_entries.items(), key=lambda kv: -len(kv[1])):
        # 按"不同天"计数：一天里说十遍不算十次，得跨三天
        distinct_days = {str(e["created_at"])[:10] for e in entries}
        if len(distinct_days) < min_count:
            continue
        latest = max(entries, key=lambda e: e["created_at"])
        if latest["text"] in seen:
            continue
        seen.add(latest["text"])
        out.append(dict(topic=topic, text=latest["text"],
                        source_ids=[e["id"] for e in entries],
                        count=len(entries), days=len(distinct_days)))
    return out[:3]


def apply(nb, cand):
    """把候选变成 pending；文本原样，不改一个字。"""
    for e in nb.entries:
        if (e["text"] == cand["text"] and e["type"] == "semantic"
                and e["status"] != "deleted"):
            return None
    for e in nb.entries:
        if e["id"] in cand.get("source_ids", []):
            e["consolidated"] = True
    return nb.add(cand["text"], type="semantic", source="consolidation",
                  confidence=0.60, status="pending", importance=0.75)
