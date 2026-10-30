# -*- coding: utf-8 -*-
"""习惯：反复出现的话题，慢慢变成 routine。

不是"她记住了"，是"这事常出现"——所以只在简报里给一句"你最近常提起X"，
不进断言、不当记忆用。

规则：最近 N 天、出现 ≥K 次的不同条目，取前几个二字词做话题。
"""
import datetime as dt

STOP = {"你的", "我的", "我们", "最近", "今天", "上次", "这个", "那个",
        "一些", "有点", "还是", "就是", "什么", "时候"}


def detect(nb, now=None, days: int = 14, min_count: int = 3):
    now = now or dt.datetime.now()
    cutoff = now - dt.timedelta(days=days)
    counts = {}
    for e in nb.live():
        if e.get("status") == "pending":
            continue
        try:
            t = dt.datetime.strptime(e["created_at"], "%Y-%m-%dT%H:%M:%S")
        except Exception:
            t = now
        if t < cutoff:
            continue
        text = e["text"]
        grams = {text[i:i + 2] for i in range(max(0, len(text) - 1))}
        grams = {g for g in grams
                 if g not in STOP and not g.startswith(("你", "我", "的"))}
        for g in grams:
            counts[g] = counts.get(g, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: -kv[1])
    return [dict(topic=k, count=v) for k, v in ranked if v >= min_count][:5]
