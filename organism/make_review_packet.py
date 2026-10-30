# -*- coding: utf-8 -*-
"""把成对题拼成一个可以直接发给人/LLM 的 txt（不含答案）。"""
import argparse
import glob
import os
import re

NUM = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二"]

HEAD = """【说明】

这是{cn}道二选一的判断题。材料是同一个体的**行为记录**（不是对话），
每条记录是若干天的流水：她什么时候醒、吃没吃、出没出门、见没见人、睡得怎么样。

每一题给两份记录：**同一个世界、同一串运气、同样过了五天**。
其中一份是完整的她；另一份少了六个系统之一（吃、睡、应激、免疫、依恋、昼夜，可能是任何一个）。
两份的差别只在于「少了什么」。

请对每一题回答：**哪一份更像「一个真实的人在过自己的日子」？**
可以答「分不出」——分不出是有价值的答案，请不要为了答题而猜。
每题再给一句理由（她哪里不对劲，或者为什么分不出）。

请按这个格式回复：

{lines}

（答案会与一份未给出的对照表核对；先不要问我要答案。）

"""


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="evidence/p0/blind_pairs")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    files = sorted(glob.glob(os.path.join(args.src, "pair*.txt")))
    out = args.out or os.path.join(args.src, "FOR_REVIEW.txt")
    n = len(files)
    lines = "\n".join("第%s题：甲 / 乙 / 分不出 —— 一句话理由" % NUM[i] for i in range(n))
    parts = [HEAD.format(cn=NUM[n - 1], lines=lines)]

    for i, path in enumerate(files):
        with open(path, encoding="utf-8") as f:
            body = f.read().strip()
        parts.append("=" * 40 + "\n第%s题\n" % NUM[i] + "=" * 40 + "\n")
        parts.append(body + "\n\n")

    text = "".join(parts)
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)

    # 自检：12 份文档两两不同
    blocks = [b.split("==========")[0].strip() for b in re.split(r"【甲】|【乙】", text)[1:]]
    print("wrote %s (%d chars, %d docs, %d unique)" % (
        out, len(text), len(blocks), len(set(blocks))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
