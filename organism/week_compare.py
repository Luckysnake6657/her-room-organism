# -*- coding: utf-8 -*-
"""同一个体的两周对比：安静周 vs 威胁密集周。

为什么不用消融做这件事：消融会改变"她是谁"，而"哪份更像在过日子"在
"更真实"与"更健康"之间有歧义——应激被拆掉的那份反而更顺，评审会选它。
同一个体两周对比没有这个问题：身体是同一个人，只有世界不同。

用法：python -m organism.week_compare --out evidence/p0/week_pairs
"""
import argparse
import os
import random

from . import params as P
from .render import render_run
from .sim import Sim

README = """十二道题。每题给**同一个人的两周**：同样五天，一个安静周，一个麻烦周。

麻烦周里，夜里总有动静，白天也更容易出岔子。

请对每一题回答：**哪一周她状态更不对劲**（更累、更烦、更不像平时的她）？
可以答「分不出」——分不出是有价值的答案，不要猜。
每题再给一句理由。

请按这个格式回复：
第…题：甲 / 乙 / 分不出 —— 一句话理由

（答案会与一份未给出的对照表核对。）
"""

HEAD = """【说明】

这是十二道二选一的判断题。材料是同一个人的**行为记录**。

每一题给同一个人的**两周**：同一套身体、同一串运气，只是世界不同——
一个安静周，一个麻烦周（夜里总有动静）。
注意：两份记录里**身体是同一个**，不存在"哪份更健康"的问题，
问的是"哪一周她更不对劲"。

请按格式回答：甲 / 乙 / 分不出 + 一句理由。
可以答「分不出」，不要为了答题而猜。

"""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="evidence/p0/week_pairs")
    ap.add_argument("--seed", type=int, default=201)
    ap.add_argument("--days", type=int, default=5)
    args = ap.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    rng = random.Random(4242)
    key = []
    parts = [HEAD]
    NUM = ("一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二")
    for i in range(12):
        seed = args.seed + i
        quiet = Sim(seed, (), P.MAIN_NOISE_BASE + seed, "allostatic", P.DAYS).run()
        rough = Sim(seed, (), P.MAIN_NOISE_BASE + seed, "allostatic", P.DAYS,
                    challenge="dense").run()
        tq = render_run(quiet, seed, args.days)
        tr = render_run(rough, seed, args.days)
        # 侧别平衡：单数题安静在甲，双数题安静在乙 → 恒答一侧得 6/12
        quiet_first = (i % 2 == 0)
        a, b = (("quiet", tq), ("rough", tr)) if quiet_first else (("rough", tr), ("quiet", tq))
        with open(os.path.join(args.out, "pair%02d.txt" % (i + 1)), "w", encoding="utf-8") as f:
            f.write("【甲】\n" + a[1] + "\n\n【乙】\n" + b[1] + "\n")
        key.append("第%02d题\t甲=%s\t乙=%s\t更不对劲=%s" % (
            i + 1, a[0], b[0], "甲" if a[0] == "rough" else "乙"))
        parts.append("=" * 40 + "\n第%s题\n" % NUM[i] + "=" * 40 + "\n")
        parts.append("【甲】\n" + a[1] + "\n\n【乙】\n" + b[1] + "\n\n")

    with open(os.path.join(args.out, "README.txt"), "w", encoding="utf-8") as f:
        f.write(README)
    with open(os.path.join(args.out, "key.txt"), "w", encoding="utf-8") as f:
        f.write("全部写完再看。\n" + "\n".join(key) + "\n")
    with open(os.path.join(args.out, "FOR_REVIEW.txt"), "w", encoding="utf-8") as f:
        f.write("".join(parts))
    correct_always_yi = sum(1 for k in key if k.endswith("=乙"))
    print("wrote 12 week-pairs to %s (always-乙 scores %d/12)" % (
        args.out, correct_always_yi))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
