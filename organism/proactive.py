# -*- coding: utf-8 -*-
"""主动开口：多理由 + 可用性 − 打扰成本（先验权重）。

输出 speak/wait + 理由，不生成文字。
"""
COST = 0.25
THRESHOLD = 0.35


def _hour(now):
    import time
    return time.localtime(now).tm_hour


def decide(body, now=None, last_contact_min=0.0, pending_unanswered=False,
           sensors=None, relation="owner_private", busy=False):
    import time
    now = time.time() if now is None else float(now)
    reasons = []
    score = 0.0
    h = _hour(now)
    s = sensors or {}

    if s.get("presence") is True:
        score += 0.25
        reasons.append("看到他在")
    if last_contact_min >= 24 * 60:
        score += 0.35
        reasons.append("一天多没聊")
    elif last_contact_min >= 8 * 60:
        score += 0.25
        reasons.append("大半天没聊")
    if pending_unanswered:
        score += 0.30
        reasons.append("她问过还没回")
    l = float(getattr(body, "l", 0.0))
    if l > 0.60:
        score += 0.20
        reasons.append("有点孤独")
    e = float(getattr(body, "e", 0.5))
    if e > 0.80:
        score += 0.10
        reasons.append("精神好想分享")

    avail = 0.0
    if s.get("presence") is True:
        avail += 0.20
    if not busy:
        avail += 0.10

    if h < 6:
        score -= 0.40
        reasons.append("凌晨")
    elif h >= 23:
        score -= 0.20
        reasons.append("很晚了")

    total = score + avail - COST
    silent = h < 6          # 0–6 点硬静默（预注册）
    speak = (relation == "owner_private" and not busy and not silent
             and total > THRESHOLD)
    if silent:
        reasons.append("静默时段")
    return dict(speak=speak, score=round(total, 3), reasons=reasons,
                cost=COST, relation=relation)
