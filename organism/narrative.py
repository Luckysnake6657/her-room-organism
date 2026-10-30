# -*- coding: utf-8 -*-
"""叙事层（影子）：用她自己的日记/记忆原话，拼一段第一人称"这几天"。

只引用她写过的话，不总结成旁白，不编因果。
"""
import json
import os
import time

NB = "evidence/p3/cmw_native/notebook.json"


def _recent(entries, days=7, limit=3):
    now = time.time()
    out = []
    for e in entries:
        if e.get("status") == "deleted":
            continue
        t = e.get("text") or ""
        ts = e.get("t") or e.get("created") or 0
        try:
            ts = float(ts)
        except Exception:
            ts = 0.0
        if ts and ts > 1e12:
            ts /= 1000.0
        fresh = (not ts) or (now - ts <= days * 86400)
        if fresh and len(t) >= 8:
            out.append((ts, t))
    out.sort(reverse=True)
    return [t for _, t in out[:limit]]


def build(days=7):
    try:
        d = json.load(open(NB, encoding="utf-8"))
        entries = d.get("entries", [])
    except Exception:
        return dict(text="", sources=[])
    picks = _recent(entries, days=days, limit=3)
    if not picks:
        return dict(text="", sources=[])
    body = "；".join("“%s”" % p[:40] for p in picks)
    text = "这几天我记着：%s。" % body
    return dict(text=text, sources=picks)
