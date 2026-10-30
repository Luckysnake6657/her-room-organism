# -*- coding: utf-8 -*-
"""用户模型：从 social-v2 最近消息估他的作息（聚合统计，不存原文）。"""
import json
import os
import time

SRC = os.environ.get("QQ_STATE", "state/social-v2.json")
OUT = "evidence/p3/usermodel.json"


def _records(path=SRC):
    d = json.load(open(path, encoding="utf-8"))
    out = []
    for conv in (d.get("conversations") or {}).values():
        for m in (conv.get("recentMessages") or []):
            if not m.get("isOwner") or m.get("isSelf"):
                continue
            t = float(m.get("time") or 0)
            if t > 1e12:
                t /= 1000.0
            if t > 0 and m.get("text"):
                out.append((t, str(m["text"])))
    out.sort()
    return out


def fit(records):
    if not records:
        return None
    hours = [0] * 24
    for t, _ in records:
        hours[time.localtime(t).tm_hour] += 1
    total = sum(hours)
    prob = [round((c + 1) / (total + 24), 4) for c in hours]
    lens = sorted(len(x) for _, x in records)
    neg = sum(1 for _, x in records if any(k in x for k in ("烦", "累", "不想", "难受", "算了")))
    return dict(n=len(records), hour_prob=prob, hour_counts=hours,
                len_p50=lens[len(lens) // 2],
                neg_rate=round(neg / len(records), 3),
                updated=time.time())


def load(path=None):
    try:
        return json.load(open(path or OUT, encoding="utf-8"))
    except Exception:
        return None


def fit_from_state(path=SRC):
    m = fit(_records(path))
    if m:
        save(m)
    return m


def active_prob(model, now=None):
    now = time.time() if now is None else float(now)
    if not model:
        return 0.5
    return float(model["hour_prob"][time.localtime(now).tm_hour])


def save(model, path=None):
    p = path or OUT
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(model, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
