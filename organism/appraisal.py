# -*- coding: utf-8 -*-
"""评价融合：把所有输入合成一个"这件事对我意味着什么"。

权重是**先验设定**（见 docs/APPRAISAL-PREREG.md），不做拟合。
输出只给增量，最终感受仍由 affect.infer 统一算。
"""

# 先验权重（可审计）
W_PRESENCE_IN = 0.08      # 摄像头看到人
W_PRESENCE_OUT = -0.18    # 长时间没看到人
W_DARK = -0.05            # 屋里很暗
W_NEED = 0.04             # 他的话里有求助/靠近
W_LONELY = -0.08           # 独处太久
W_RELIEF = 0.06           # 他回来/回应


def fuse(body, sensors=None, text="", memories=(), relation="owner_private",
         away_min=0.0):
    """返回 delta_valence / delta_arousal / extra_components / reasons。"""
    d = 0.0
    reasons = []
    comps = []
    s = sensors or {}
    close = 1.0 if relation == "owner_private" else 0.3

    if s.get("presence") is True:
        d += W_PRESENCE_IN * close
        reasons.append("看到他在")
    elif s and s.get("presence") is False:
        if away_min >= 30:
            d += W_PRESENCE_OUT * close
            d += W_LONELY * close
            comps.append("孤单")
            reasons.append("很久没看到人")

    if s and float(s.get("light") or 1.0) < 0.12:
        d += W_DARK
        reasons.append("屋里很暗")

    t = str(text or "")
    if any(k in t for k in ("陪我", "聊聊", "在吗", "想你", "难受")):
        d += W_NEED * close
        reasons.append("他在靠近")

    if body is not None:
        l = float(getattr(body, "l", 0.0))
        if l > 0.6 and away_min >= 30:
            d += W_LONELY
            if "孤单" not in comps:
                comps.append("孤单")
            reasons.append("本来就孤独")

    # 他回来（presence 从无到有）由调用方给 away_min 小 + presence true 表示
    if s.get("presence") is True and away_min < 5:
        d += W_RELIEF * close
        reasons.append("他回来了")

    return dict(delta_valence=round(max(-0.25, min(0.25, d)), 3),
                delta_arousal=0.0,
                extra_components=comps[:2],
                reasons=reasons)
