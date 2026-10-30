# -*- coding: utf-8 -*-
"""性格漂移：人会变，但慢、有界、有来源。

只动一条特质（人物卡的"话少"），按**周**汇总，不按单句：

- 这一周 regard 净涨 ≥ 阈值 → 她愿意多说一点
- 净跌 ≤ −阈值 → 她收回一点
- 一年最多 ±0.15（对 words_mul 的绝对值）

不是好感条：它改的是"她这个人被磨成了什么样"，不是"她多喜欢你"。
"""
LIMIT = 0.15
WEEKLY_STEP = 0.006
SIGNAL = 0.015


def _clip(x, lo, hi):
    return max(lo, min(hi, x))


def weekly(body, regard_delta: float) -> float:
    d = float(getattr(body, "trait_drift", 0.0))
    if regard_delta >= SIGNAL:
        d += WEEKLY_STEP
    elif regard_delta <= -SIGNAL:
        d -= WEEKLY_STEP
    d = _clip(d, -LIMIT, LIMIT)
    body.trait_drift = d
    log = getattr(body, "trait_log", None)
    if log is None:
        log = []
        body.trait_log = log
    log.append(dict(week_delta=round(regard_delta, 3), drift=round(d, 4)))
    del log[:-60]
    return d


def words_mul(persona, body) -> float:
    base = persona.words_mul if persona is not None else 1.0
    return _clip(base + float(getattr(body, "trait_drift", 0.0)), 0.45, 0.95)
