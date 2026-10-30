# -*- coding: utf-8 -*-
"""遗忘：强度随时间衰减，访问会刷新；低到一定程度变"模糊"，不硬删。

艾宾浩斯式的近似：强度按半衰期衰减，访问时回一点。
- strength >= 0.5 active
- 0.2–0.5 fuzzy（还能想起大概，细节不确定）
- < 0.2 faded（不再主动提起，但保留记录）

硬删除只由用户发起（/forget 或 /delete）。
"""
import datetime as dt

HALF_LIFE_DAYS = 45.0
TOUCH_GAIN = 0.15


def _days_since(ts: str, now: dt.datetime) -> float:
    try:
        t = dt.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")
    except Exception:
        return 0.0
    return max(0.0, (now - t).total_seconds() / 86400.0)


def strength_now(entry, now=None) -> float:
    now = now or dt.datetime.now()
    base = float(entry.get("strength", 1.0))
    days = _days_since(entry.get("last_access", entry["created_at"]), now)
    return base * (0.5 ** (days / HALF_LIFE_DAYS))


def state(entry, now=None) -> str:
    s = strength_now(entry, now)
    if s >= 0.50:
        return "active"
    if s >= 0.20:
        return "fuzzy"
    return "faded"


def touch(entry, now=None):
    """被检索到 = 用了一次，强度回一点。"""
    now = now or dt.datetime.now()
    s = strength_now(entry, now)
    entry["strength"] = min(1.0, s + TOUCH_GAIN)
    entry["last_access"] = now.strftime("%Y-%m-%dT%H:%M:%S")
    return entry


def sweep(nb, now=None):
    """批量结算：更新 strength 与 status（faded 只改状态，不删）。"""
    now = now or dt.datetime.now()
    counts = dict(active=0, fuzzy=0, faded=0)
    for e in nb.live():
        e["strength"] = round(strength_now(e, now), 4)
        st = state(e, now)
        counts[st] += 1
        if st == "faded" and e["status"] == "confirmed":
            e["status"] = "faded"
        elif st != "faded" and e["status"] == "faded":
            e["status"] = "confirmed"
    nb.save()
    return counts
