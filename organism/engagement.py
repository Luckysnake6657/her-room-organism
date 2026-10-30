# -*- coding: utf-8 -*-
"""介入定价：这次要不要说话、说多少。

依据：Horvitz 1999 混合主动；When Should the Agent Speak? (TMLR 2026)
—— intervene iff E[benefit] > E[cost of interrupting]。

不做 life/task 二分类；输出 now / brief / later。
"""
from . import params as P

STRONG = ("帮我", "看一下", "看看这个", "查一下", "写个", "改一下", "算一下",
          "翻译", "报错", "代码", "文件", "弄好", "再试", "读不到", "检查", "报给")
WEAK = ("吗", "?", "？", "怎么", "能不能", "可以", "行不行", "试试")


def _clip(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def price(body, text: str, regard: float = None) -> dict:
    t = str(text or "")
    if any(m in t for m in STRONG):
        explicit = 1.0
    elif any(m in t for m in WEAK):
        explicit = 0.5
    else:
        explicit = 0.0

    r = float(getattr(body, "regard", 0.5) if regard is None else regard)
    benefit = 0.5 * explicit + 0.3 * 0.6 + 0.2 * r

    cost = (0.35 * float(body.a)
            + 0.25 * (1.0 - float(body.e))
            + 0.20 * min(1.0, float(body.D()) / 2.0)
            + 0.10 * float(getattr(body, "u", 0.0)))
    uncertainty = 0.10 if explicit == 0.5 else 0.0
    net = benefit - cost - uncertainty

    if net >= 0.30:
        decision = "now"
    elif net >= -0.10:
        decision = "brief"
    else:
        decision = "later"
    return dict(decision=decision, net=round(net, 3),
                benefit=round(benefit, 3), cost=round(cost, 3),
                explicit=explicit)
