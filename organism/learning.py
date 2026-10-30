# -*- coding: utf-8 -*-
"""学习闭环：预测误差 → 缓慢更新参数（有周上限、审计、可回滚）。"""
import json
import os
import time

STATE = "evidence/p3/learning.json"
LOG = "evidence/p3/learning_log.jsonl"
DEFAULTS = {"expressiveness": 0.50, "initiative": 0.50}
RATE = 0.01
WEEK_CAP = 0.02
LO, HI = 0.05, 0.95


def _week(now):
    return time.strftime("%Y-W%W", time.localtime(now))


def load(path=STATE):
    try:
        d = json.load(open(path, encoding="utf-8"))
        d.setdefault("params", dict(DEFAULTS))
        d.setdefault("week", _week(time.time()))
        d.setdefault("week_delta", {})
        return d
    except Exception:
        return dict(params=dict(DEFAULTS), week=_week(time.time()), week_delta={})


def _save(d, path=STATE):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)


def update(key, error, now=None, path=STATE, log_path=LOG, reason=""):
    """error in [-1,1]；返回 (旧值, 新值)。"""
    now = time.time() if now is None else float(now)
    d = load(path)
    if d.get("week") != _week(now):
        d["week"] = _week(now)
        d["week_delta"] = {}
    old = float(d["params"].get(key, DEFAULTS.get(key, 0.5)))
    delta = max(-RATE, min(RATE, RATE * float(error)))
    used = float(d["week_delta"].get(key, 0.0))
    room = WEEK_CAP - abs(used)
    if room <= 0:
        delta = 0.0
    elif abs(delta) > room:
        delta = room if delta > 0 else -room
    new = round(max(LO, min(HI, old + delta)), 4)
    d["params"][key] = new
    d["week_delta"][key] = round(used + (new - old), 4)
    _save(d, path)
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(dict(t=now, key=key, old=old, new=new,
                                    error=round(float(error), 3), reason=reason),
                               ensure_ascii=False) + "\n")
    except Exception:
        pass
    return old, new


def params(path=STATE):
    return dict(load(path)["params"])
