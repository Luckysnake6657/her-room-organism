# -*- coding: utf-8 -*-
"""记忆置信分层：断言 / 对冲 / 弃权。

文献：Chow 1970（拒识）、Geifman & Elidan 2017（selective prediction）、
Guo et al. 2017（校准）、Kadavath et al. 2022（模型知道自己知道什么）。
目标：错的代价 >> 空答的代价，所以宁可对冲/弃权。
"""
ASSERT = (0.30, 0.0)   # (min score, min calibrated)
HEDGE = 0.20            # min score


MARGIN = 0.05   # top1 与 top2 分差小于此值 → 对冲


def band(scored) -> str:
    if not scored:
        return "none"
    score, entry = scored[0]
    if entry.get("contested"):
        # 被纠正过一次：永不断言，最多对冲
        return "hedge" if score >= HEDGE else "none"
    if len(scored) > 1 and (score - scored[1][0]) < MARGIN:
        return "hedge" if score >= HEDGE else "none"
    if len(scored) == 1 and score < 0.50:
        # 只有一个孤零零的低分候选：更像"提到了"，不像"答案"
        return "hedge" if score >= HEDGE else "none"
    calib = float(entry.get("calibrated", entry.get("confidence", 0.0)))
    if score >= ASSERT[0] and calib >= ASSERT[1]:
        return "assert"
    if score >= HEDGE:
        return "hedge"
    return "none"


def note(band: str) -> str:
    """给嘴的提示：只影响措辞，不改事实。"""
    if band == "hedge":
        return ("记忆不太确定：用'我记得好像是/不太确定'，或者反问一句确认"
                "（'你说的是…那次吗'），别说得斩钉截铁。")
    if band == "none":
        return ("记忆里没有这条：别编，也别拿相关的事当答案；"
                "可以问一句'你问的是哪件事/哪只猫？'。")
    return ""
