# -*- coding: utf-8 -*-
"""依恋三要素的可操作定义。

文献：
- 依恋指向**特定的人**，不是泛化的社交（Bowlby, 1969/1982, *Attachment and Loss*）
- 安全基地/安全港：只在少数关系上成立（Ainsworth et al., 1978）
- 承诺 = 满意 + 投资 − 替代（Rusbult 投资模型）

我们的三条，都能测：

1. **specificity（只对你）**：门廊 NPC 的社交**不改变** regard / U / 漂移；
   只有用户的回应会。代码上已经如此，这里把它变成断言。
2. **continuity（跨时间）**：regard / 漂移 / 本子在存档、离线、重启后都还在。
3. **cost（有让渡）**：累了也愿意接你——高 regard 时接下"陪我说会儿"的概率更高，
   低 regard 时同样的疲惫会拒绝。她花的是自己的精力。
"""


def willing(body, fatigue: float = 0.0) -> bool:
    """在给定疲惫下，她愿不愿意接一次"陪我说会儿"。

    regard 高、U 低 → 更愿意；疲惫高 → 更不愿意。
    不是无条件答应：低 regard + 高疲惫会拒绝。
    """
    r = float(getattr(body, "regard", 0.5))
    u = float(getattr(body, "u", 0.0))
    score = (r - 0.5) * 2.0 - 0.6 * fatigue + 0.30 * (1.0 - u)
    return score > 0.0


def relation_snapshot(body) -> dict:
    return dict(regard=round(float(getattr(body, "regard", 0.5)), 6),
                u=round(float(getattr(body, "u", 0.0)), 6),
                drift=round(float(getattr(body, "trait_drift", 0.0)), 6))


def npc_contact(body, times: int = 10) -> dict:
    """门廊那个人的社交；不该动关系状态。"""
    for _ in range(times):
        body.contact(npc=True)
    return relation_snapshot(body)
