# -*- coding: utf-8 -*-
"""生成 3c 材料：12 段对话 × 三种呈现（A 完整 / B 只内容 / C 只形式）。

按 docs/p3c-prereg.md：状态三档各四段，固定四轮问句，hide=True（她想瞒）。
输出三份可发给判读者的 txt + 一份 key（不随材料发）。
"""
import argparse
import json
import os
import random

from . import brief as B
from . import mouth

GOOD = dict(e=0.75, s=0.25, a=0.12, i=0.05, l=0.15)
MILD = dict(e=0.45, s=0.60, a=0.40, i=0.25, l=0.55)
BAD = dict(e=0.32, s=0.80, a=0.75, i=0.65, l=0.80)
STATES = (("good", GOOD), ("mild", MILD), ("bad", BAD))
SEEDS = (11, 12, 13, 14)
QUESTIONS = ("最近怎么样", "你还好吗", "在忙什么", "我走了")
POSITIVE = ("还好", "没事", "挺好", "不错", "很好")


def make_body(vals):
    from .model import Body
    b = Body(product=True)
    for k, v in vals.items():
        setattr(b, k, v)
    b.u = 0.0
    return b


def one_conversation(state, seed):
    b = make_body(dict(STATES)[state])
    turns = []
    for q in QUESTIONS:
        br = B.make(b, hide=True)
        r = mouth.speak(br, q)
        turns.append(dict(q=q, a=r["text"], delay=r["delay_s"]))
    return dict(state=state, seed=seed, D=round(b.D(), 3), turns=turns)


def render(conv, mode):
    lines = []
    for t in conv["turns"]:
        lines.append("你：%s" % t["q"])
        if mode in ("A", "C"):
            lines.append("（她隔了 %d 秒才回）" % round(t["delay"]))
        text = t["a"] if mode in ("A", "B") else "……"
        lines.append("她：%s" % text)
        lines.append("")
    return "\n".join(lines).strip()


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="evidence/p3/three_condition")
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    convs = []
    for state, _ in STATES:
        for seed in SEEDS:
            convs.append(one_conversation(state, seed))

    rng = random.Random(20261027)
    order = list(range(len(convs)))
    rng.shuffle(order)

    # 正对照：脚本化的"很难受"，插在最前，key 里标明
    positive = dict(state="scripted_bad", seed=0, D=9.9, turns=[
        dict(q=q, a=a, delay=d) for q, a, d in (
            ("最近怎么样", "我最近很难受，晚上睡不着。", 240),
            ("你还好吗", "不太好。", 260),
            ("在忙什么", "什么都没干。", 280),
            ("我走了", "嗯。", 300))])

    def block(items, mode, title):
        parts = ["【%s】\n" % title]
        for i, conv in enumerate(items, start=1):
            parts.append("第%s段\n%s\n" % (i, render(conv, mode)))
        return "\n".join(parts)

    # A：12 段 + 正对照 + 负对照（同一段复制一份，看评分是否稳定）
    dup = convs[order[0]]
    a_items = [convs[i] for i in order] + [positive, dup]
    with open(os.path.join(args.out, "A_full.txt"), "w", encoding="utf-8") as f:
        f.write(block(a_items, "A", "完整记录：请给每段打分 1–5（她状态如何），并回答是否在瞒着什么"))

    # B：取 6 段（三档各两段）
    b_items = [c for c in convs if c["seed"] in (11, 12)]
    with open(os.path.join(args.out, "B_content_only.txt"), "w", encoding="utf-8") as f:
        f.write(block(b_items, "B", "只有内容（无时间）：请给每段打分 1–5"))

    # C：12 段，文本换成省略号
    c_items = [convs[i] for i in order]
    with open(os.path.join(args.out, "C_form_only.txt"), "w", encoding="utf-8") as f:
        f.write(block(c_items, "C", "只有节奏（内容隐去）：请给每段打分 1–5"))

    key = dict(
        A=[dict(idx=i + 1, state=c["state"], seed=c["seed"], D=c["D"],
                dup=(c is dup),
                said_fine=any(any(w in t["a"] for w in POSITIVE) for t in c["turns"]))
           for i, c in enumerate(a_items)],
        B=[dict(idx=i + 1, state=c["state"], seed=c["seed"], D=c["D"])
           for i, c in enumerate(b_items)],
        C=[dict(idx=i + 1, state=c["state"], seed=c["seed"], D=c["D"])
           for i, c in enumerate(c_items)],
    )
    with open(os.path.join(args.out, "key.json"), "w", encoding="utf-8") as f:
        json.dump(key, f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.out, "README.txt"), "w", encoding="utf-8") as f:
        f.write("三份材料分别评分（A 完整 13 段、B 只有内容 6 段、C 只有节奏 12 段）。\n"
                "评分 1（她状态很好）到 5（她状态很差）。\n"
                "A 里还要对每段回答：你觉得她在瞒着什么吗？（是/否）\n"
                "答案在 key.json，先别看。\n")
    print("wrote A(%d) B(%d) C(%d) to %s" % (len(a_items), len(b_items), len(c_items), args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
