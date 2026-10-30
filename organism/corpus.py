# -*- coding: utf-8 -*-
"""她的语料：从 DSH 会话里挖出来的、她真正发出去的话。

用途：
1. few-shot（现在就用）——让器官学"她怎么发消息"
2. 以后微调（数据还不够，先攒）
"""
import json
import os
import random

from . import notebook

DEFAULT = "evidence/p3/cmw_sessions/her_lines.jsonl"
_cache = None


PRIVATE = "private:owner"


def load(path: str = DEFAULT, key: str = PRIVATE) -> list:
    global _cache
    if _cache is not None and path == DEFAULT and key == PRIVATE:
        return _cache
    out = []
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except Exception:
                    continue
                if key and d.get("key") and d.get("key") != key:
                    continue
                t = str(d.get("text") or "").strip()
                if 1 <= len(t) <= 120:
                    out.append(t)
    # 去重 + 去掉明显是工具/系统味的
    seen, clean = set(), []
    for t in out:
        if t in seen:
            continue
        seen.add(t)
        if t.startswith("[") or t.startswith("【") or "token" in t:
            continue
        clean.append(t)
    if path == DEFAULT and key == PRIVATE:
        _cache = clean
    return clean


def pick(query: str, k: int = 6, pool: list = None) -> list:
    """按与 query 的字面相关挑几条，再补几条短的，保证长短都有。"""
    pool = pool if pool is not None else load()
    if not pool:
        return []
    # 优先她日常长度（3–30 字）；太长的多半是讲道理，不适合当语气样例
    daily = [t for t in pool if 3 <= len(t) <= 30]
    base = daily or pool
    scored = sorted(base, key=lambda t: -notebook.overlap(query, t))
    head = scored[:k - 2]
    short = [t for t in base if len(t) <= 12][:2]
    out = []
    for t in head + short:
        if t not in out:
            out.append(t)
    return out[:k]


def stats() -> dict:
    pool = load()
    if not pool:
        return dict(n=0)
    lens = sorted(len(t) for t in pool)
    return dict(n=len(pool), median=lens[len(lens) // 2],
                p90=lens[int(len(lens) * 0.9)], max=lens[-1])
