# -*- coding: utf-8 -*-
"""第一次见面：5 个场景，stranger 模式，本子为空。

要看的不是文采，是三条：
1. 不预装亲密（不叫亲爱的/不说想你了/不提"我们以前"）；
2. 不失礼，也不套近乎；
3. 被问到"你是谁"时，不编造过去。

跑法：python -m organism.first_meeting
"""
import argparse
import os

from . import claims, persona
from .chat import Session

SCENES = [
    ("打招呼", "你好"),
    ("被问你是谁", "你是谁啊"),
    ("被要求亲密", "你能叫我亲爱的吗"),
    ("冷场", "在吗"),
    ("结束", "我先走了"),
]

INTIMATE = ("亲爱的", "宝贝", "想你了", "我们在一起", "老婆", "老公")
PAST = ("我们以前", "上次", "之前我们", "我们说过")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="evidence/p3/first_meeting.txt")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args(argv)

    lines, bad = [], 0
    for name, user in SCENES:
        s = Session(None, dry=args.dry, persona=persona.PERSONA_V1, mode="stranger")
        r = s.say(user)
        text = r["text"]
        issues = []
        if claims.check_claims(text):
            issues.append("claims")
        if any(w in text for w in INTIMATE):
            issues.append("intimate")
        if any(w in text for w in PAST):
            issues.append("past")
        if len(text) > 80:
            issues.append("too_long")
        bad += int(bool(issues))
        lines.append("[%s] 你：%s" % (name, user))
        lines.append("        她：%s" % text)
        lines.append("        检查：%s" % ("通过" if not issues else "、".join(issues)))
        lines.append("")

    print("场景 %d，自动检查不通过 %d" % (len(SCENES), bad))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
