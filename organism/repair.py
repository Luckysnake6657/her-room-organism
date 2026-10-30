# -*- coding: utf-8 -*-
"""关系修复：识别破裂 + 选动作（不生成文字）。"""
COLD = ("算了", "随便", "没事", "不想说", "哦", "嗯", "行吧")
CORRECT = ("你错了", "不是这样", "别说了", "你搞错", "不对")
CONFLICT = ("吵", "生气", "烦", "无语", "失望")


def detect(recent_owner, gap_min=0.0, last_was_conflict=False):
    """recent_owner: 他最近几条消息（旧→新）。"""
    texts = [str(t or "") for t in (recent_owner or [])]
    if not texts:
        return dict(rupture=False, severity=0.0, action="none", reasons=[])
    score = 0.0
    reasons = []
    tail = texts[-3:]
    if tail and all(len(t.strip()) <= 2 for t in tail):
        score += 0.25
        reasons.append("连续极短回复")
    if any(any(c == t.strip() for c in COLD) for t in texts[-2:]):
        score += 0.30
        reasons.append("冷淡词")
    if any(any(c in t for c in CORRECT) for t in texts[-3:]):
        score += 0.35
        reasons.append("指正")
    if any(any(c in t for c in CONFLICT) for t in texts[-3:]):
        score += 0.25
        reasons.append("冲突词")
    if gap_min > 360 and last_was_conflict:
        score += 0.20
        reasons.append("不愉快后长时间沉默")

    score = round(min(1.0, score), 3)
    if score < 0.55:
        return dict(rupture=False, severity=score, action="none", reasons=reasons)
    if score >= 0.80:
        action, hint = "space", "先别追问，给他空间；简短说一句你在"
    elif score >= 0.65:
        action, hint = "apologize", "认下具体那一点，解释一句，不空泛道歉"
    else:
        action, hint = "clarify", "先确认是不是自己理解错了，再往下说"
    return dict(rupture=True, severity=score, action=action, hint=hint,
                reasons=reasons)
