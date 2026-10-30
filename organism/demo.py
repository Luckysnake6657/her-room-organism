# -*- coding: utf-8 -*-
"""一条完整的演示：离开一个月 → 回来 → 问结算 → 每天联系 → 她重新先开口。

用法：
    python -m organism.demo            # 不加载模型（快，用占位文本）
    python -m organism.demo --real     # 真的用本地 1.5B 说话
"""
import argparse
import json
import os

from . import params as P
from .chat import Session


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--path", default="evidence/p3/demo_session.json")
    ap.add_argument("--days-away", type=int, default=30)
    args = ap.parse_args(argv)
    if os.path.exists(args.path):
        os.remove(args.path)

    s = Session(args.path, dry=not args.real)
    s._save()
    print("== 刚认识 ==", s.peek()["state"], "| u =", round(s.peek()["u"], 3))

    # 真的离线：把存档时间戳拨回去，让她按挂钟补算
    st = json.load(open(args.path, encoding="utf-8"))
    st["saved_at"] -= args.days_away * 86400
    with open(args.path, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False)

    s2 = Session(args.path, dry=not args.real)
    gap = s2.last_gap or {}
    print("== 回来 ==", s2.peek()["state"], "| u =", round(s2.peek()["u"], 2),
          "| 慢性 =", round(sum(s2.sim.body.chronic.values()), 1))
    print("  补算了 %.0f 天；结算：" % gap.get("days_alone", 0), s2.say("这段时间")["text"])

    g = s2.greeting()
    print("  回来时她先开口？", (g or {}).get("text", "没有"))

    print("== 连续七天联系 ==")
    for d in range(7):
        s2.say("今天怎么样")
        s2.sim.run(stop=s2.sim.t + P.MIN_PER_DAY)
        g = s2.greeting()
        print("  第 %d 天 u=%.2f 主动=%s %s" % (
            d + 1, s2.sim.body.u, "有" if g else "无", (g or {}).get("text", "")))
        s2._save()

    print("== 之后两天没人说话 ==")
    for d in range(2):
        s2.sim.run(stop=s2.sim.t + P.MIN_PER_DAY)
        g = s2.greeting()
        print("  第 %d 天 孤独=%.2f 主动=%s %s" % (
            d + 1, s2.sim.body.l, "有" if g else "无", (g or {}).get("text", "")))
        s2._save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
