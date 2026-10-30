# -*- coding: utf-8 -*-
"""元记忆：按检索分数决定怎么说。

≥0.7  "本子上写着……"（确定）
0.4–0.7 "我好像记得……"（模糊）
<0.4  "这个我没记"（拒）

措辞必须对应分数，不能凭模型心情。
"""


def phrase(tier: str) -> str:
    return {
        "strong": "本子上写着",
        "fuzzy": "我好像记得",
        "none": "这个我没记",
    }.get(tier, "这个我没记")


def tier_of(scored) -> str:
    if not scored:
        return "none"
    return tier_from_score(scored[0][0])


def tier_from_score(s: float) -> str:
    if s >= 0.70:
        return "strong"
    if s >= 0.40:
        return "fuzzy"
    return "none"
