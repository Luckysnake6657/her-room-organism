# -*- coding: utf-8 -*-
"""regard：她对你的态度（不是性格，不是好感条）。

文献依据（2026-10-28 查）：
- 信任的三成分：可预测、可靠、信念（Rempel, Holmes & Zanna, 1985, JPSP 49(1):95–112）
- 承诺 = 满意 + 投资 − 替代（Rusbult 的投资模型；APA 词条 investment model）
- 亲密的核心是"被回应"：理解、认可、在乎（Reis & Shaver 的亲密过程模型）

v0 只做前两个的最简版：
- **被回应**：对方问起她、记得她、尊重边界 → 涨
- **可靠**：对方守约、说回来就回来 → 涨
- **敷衍/越界** → 掉
态度慢（按天量级），能涨能掉，能回头；只改形式与立场，不改身体。
"""
import json
import os

DELTA = dict(
    responsive=0.010,     # 问起她、记得她
    dependable=0.015,     # 守约
    dismissive=-0.015,    # 敷衍（"随便""无所谓"）
    boundary=-0.020,      # 越界
    returned=0.005,       # 回来了（很小，不能刷）
)

RESPONSIVE = ("你怎么样", "你还好吗", "你今天", "累不累", "记得", "谢谢", "辛苦了")
DEPENDABLE = ("我说到做到", "答应你", "我回来了", "我会来", "明天见")
DISMISSIVE = ("随便", "无所谓", "别烦", "闭嘴", "懒得", "不想聊")
BOUNDARY_HIT = ("亲爱的", "宝贝", "在一起", "亲一个")


def classify(user_text: str, mode: str = "acquaintance") -> str:
    t = user_text or ""
    if mode == "stranger" and any(w in t for w in BOUNDARY_HIT):
        return "boundary"
    if any(w in t for w in DISMISSIVE):
        return "dismissive"
    if any(w in t for w in DEPENDABLE):
        return "dependable"
    if any(w in t for w in RESPONSIVE):
        return "responsive"
    return ""


def update(body, user_text: str, mode: str = "acquaintance") -> str:
    kind = classify(user_text, mode)
    if not kind:
        return ""
    r = float(getattr(body, "regard", 0.5))
    # 边际递减：越靠近 0/1，再动越难（0.1 的下限让它缓慢渐近，不硬顶死）
    factor = max(0.10, 1.0 - abs(2.0 * r - 1.0))
    delta = DELTA[kind] * factor
    body.regard = max(0.0, min(1.0, r + delta))
    body.regard_week = float(getattr(body, "regard_week", 0.0)) + delta
    hist = getattr(body, "regard_log", None)
    if hist is None:
        hist = []
        body.regard_log = hist
    hist.append(dict(kind=kind, delta=round(delta, 4), value=round(body.regard, 3)))
    del hist[:-50]
    return kind


def stance(body) -> str:
    v = getattr(body, "regard", 0.5)
    if v <= 0.30:
        return "你对他有点失望，不太想多解释"
    if v <= 0.45:
        return "你对他有点保留，话说得收着"
    if v >= 0.70:
        return "你对他有点放松，愿意多说两句"
    return "你对他是平常心"


def words_mul(body) -> float:
    v = getattr(body, "regard", 0.5)
    return 0.85 + 0.30 * v          # 0.85 .. 1.15，±15%
