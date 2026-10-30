# -*- coding: utf-8 -*-
"""结果记录：主动是否被接受、破裂是否修复（纯函数 + jsonl 追加）。"""
import json
import time

LOG = "evidence/p3/outcomes.jsonl"


def proactive_outcome(sent_ts, reply_ts=None, window_s=6 * 3600):
    if not reply_ts or reply_ts <= sent_ts:
        return "pending"
    if reply_ts - sent_ts <= window_s:
        return "accepted"
    return "ignored"


def repair_outcome(prev_rupture, now_rupture, turns):
    if not prev_rupture:
        return "none"
    if not now_rupture:
        return "repaired"
    if turns >= 3:
        return "failed"
    return "pending"


def log(kind, **kw):
    rec = dict(t=time.time(), kind=kind, **kw)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass
    return rec


def summary(path=LOG):
    n = {"accepted": 0, "ignored": 0, "repaired": 0, "failed": 0, "pending": 0}
    try:
        for line in open(path, encoding="utf-8"):
            d = json.loads(line)
            k = d.get("outcome")
            if k in n:
                n[k] += 1
    except Exception:
        pass
    return n
