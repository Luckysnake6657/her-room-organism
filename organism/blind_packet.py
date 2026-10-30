# -*- coding: utf-8 -*-
"""生成盲测包：七份「五天」的行为记录，标签打乱，答案另放。

用途：P0 判据 3c（人判）。不自动评分。

注意：七份必须**两两不同**，否则盲测不成立（第一版就栽在这：
三天的普通周里，免疫消融与基线逐字相同，两份文档一模一样）。
"""
import argparse
import os
import random

from . import params as P
from .render import render_run
from .sim import Sim

DOCS = (("baseline", ()),
        ("lesion_energy", ("energy",)),
        ("lesion_sleep", ("sleep",)),
        ("lesion_stress", ("stress",)),
        ("lesion_immune", ("immune",)),
        ("lesion_lonely", ("lonely",)),
        ("lesion_clock", ("clock",)))

README = """这是一组行为记录，同一天开始、同样过了五天多。
七份里有一份是完整的她，另外六份各少了一个系统。

看的时候不要找数字——本来就没有。你只需要回答两个问题：

一、哪一份最像「一个人在过日子」？
二、哪一份最不像？为什么（她哪些地方不对劲）？

把答案写下来，或者直接告诉我。答案在 key.txt，先别看。
"""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="evidence/p0/blind")
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--days", type=int, default=5)
    ap.add_argument("--challenge", default="")
    ap.add_argument("--salt", type=int, default=0,
                    help="换一个盐 = 换一种字母映射；重发包时必须换")
    args = ap.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    rng = random.Random(20261027 + args.salt)
    docs = []
    for name, lesion in DOCS:
        res = Sim(args.seed, lesion, P.MAIN_NOISE_BASE + args.seed, "allostatic",
                  P.DAYS, challenge=args.challenge or False).run()
        docs.append((name, render_run(res, args.seed, args.days)))
    rng.shuffle(docs)

    texts = [t for _, t in docs]
    if len(set(texts)) != len(texts):
        print("WARN: 有重复文档，盲测不成立；换个 seed 或加长天数")

    letters = "ABCDEFG"
    key = []
    for letter, (name, text) in zip(letters, docs):
        with open(os.path.join(args.out, "%s.txt" % letter), "w", encoding="utf-8") as f:
            f.write(text + "\n")
        key.append("%s\t%s" % (letter, name))

    with open(os.path.join(args.out, "README.txt"), "w", encoding="utf-8") as f:
        f.write(README)
    with open(os.path.join(args.out, "key.txt"), "w", encoding="utf-8") as f:
        f.write("先看完再打开。\n" + "\n".join(key) + "\n")
    print("wrote 7 docs + key to %s (seed=%d days=%d challenge=%r, distinct=%s)" % (
        args.out, args.seed, args.days, args.challenge or False,
        len(set(texts)) == len(texts)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
