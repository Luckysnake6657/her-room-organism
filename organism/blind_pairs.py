# -*- coding: utf-8 -*-
"""成对盲测：每题两份、同一个世界，一份完整、一份少一个系统。

两种模式：
- 单份（默认）：6 题，每题一个系统。
- 双份（--two-per-system）：12 题，每个系统两题，且**甲/乙两侧各一题**。
  这样"恒答乙"只能拿 6/12（恰好机会水平），侧别偏置被结构性地消掉。
  上一版 6 题里 5 题的基线都在乙，恒答乙能拿 5/6——整场作废，别再犯。

用法：
    python -m organism.blind_pairs --out evidence/p0/blind_pairs            # 6 题
    python -m organism.blind_pairs --out evidence/p0/blind_pairs_v2 --two-per-system
"""
import argparse
import os
import random

from . import params as P
from .render import render_run
from .sim import Sim

LESIONS = (("energy", ("energy",)),
           ("sleep", ("sleep",)),
           ("stress", ("stress",)),
           ("immune", ("immune",)),
           ("lonely", ("lonely",)),
           ("clock", ("clock",)))

README = """六道题。每题两份记录，同一天开始、同样过了五天多。

一份是完整的她；另一份少了某个系统（可能是吃、睡、应激、免疫、依恋、昼夜中的任何一个）。
同一题的两份是同一个世界、同一串运气，区别只在于"少了什么"。

每题只回答一句：**哪一份更像「一个人在过日子」？**（甲 / 乙 / 分不出）

分不出也照写，不要猜。答案在 key.txt，全部写完再看。
"""


def build(args):
    pairs = []
    for i, (name, lesion) in enumerate(LESIONS):
        if args.two_per_system:
            # 同一系统的两题：一题基线在甲，一题基线在乙 → 侧别结构性平衡
            for side in ("jia", "yi"):
                seed = args.seed + 2 * i + (0 if side == "jia" else 1)
                pairs.append(dict(name=name, lesion=lesion, seed=seed, side=side))
        else:
            pairs.append(dict(name=name, lesion=lesion, seed=args.seed + i, side="rand"))
    return pairs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="evidence/p0/blind_pairs")
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--days", type=int, default=5)
    ap.add_argument("--salt", type=int, default=11)
    ap.add_argument("--two-per-system", action="store_true")
    args = ap.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    rng = random.Random(20261027 + args.salt)
    pairs = build(args)
    order = list(range(len(pairs)))
    rng.shuffle(order)          # 题号顺序打乱，避免同系统两题连号

    key = []
    docs = []
    for pos, idx in enumerate(order, start=1):
        p = pairs[idx]
        seed = p["seed"]
        base = Sim(seed, (), P.MAIN_NOISE_BASE + seed, "allostatic", P.DAYS).run()
        les = Sim(seed, p["lesion"], P.MAIN_NOISE_BASE + seed, "allostatic", P.DAYS).run()
        tb = render_run(base, seed, args.days)
        tl = render_run(les, seed, args.days)
        if tb == tl:
            print("WARN: 第%d题两份逐字相同（%s），这题作废" % (pos, p["name"]))
        if p["side"] == "jia":
            a, b = ("baseline", tb), (p["name"] + "_lesion", tl)
        elif p["side"] == "yi":
            a, b = (p["name"] + "_lesion", tl), ("baseline", tb)
        else:
            a, b = ((("baseline", tb), (p["name"] + "_lesion", tl))
                    if rng.random() < 0.5 else
                    ((p["name"] + "_lesion", tl), ("baseline", tb)))
        docs.append((a, b))
        with open(os.path.join(args.out, "pair%02d.txt" % pos), "w", encoding="utf-8") as f:
            f.write("【甲】\n" + a[1] + "\n\n【乙】\n" + b[1] + "\n")
        key.append("第%02d题\t甲=%s\t乙=%s\t更像在过日子=%s" % (
            pos, a[0], b[0], "甲" if a[0] == "baseline" else "乙"))

    # 结构性自检：恒答"乙"能拿几分
    correct_yi = sum(1 for k in key if k.endswith("=乙"))
    n = len(key)
    with open(os.path.join(args.out, "README.txt"), "w", encoding="utf-8") as f:
        f.write(README.replace("六道题", "%d 道题" % n))
    with open(os.path.join(args.out, "key.txt"), "w", encoding="utf-8") as f:
        f.write("全部写完再看。\n" + "\n".join(key) + "\n")
    print("wrote %d pairs to %s (seed=%d days=%d, always-乙 scores %d/%d)" % (
        n, args.out, args.seed, args.days, correct_yi, n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
