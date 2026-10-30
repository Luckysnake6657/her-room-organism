# -*- coding: utf-8 -*-
"""感受盲测（对话版）：他先说一句，两句都是她的回答。"""
import json
import random

from . import affect, expression_short as es, model

# (他说的话, e,s,a,i,l, presence, 场景)
ITEMS = [
    ("今天过得咋样", 0.5, 0.2, 0.2, 0.2, 0.3, "他在", "普通一天"),
    ("今天过得咋样", 0.2, 0.1, 0.2, 0.1, 0.7, "他有一阵没来了", "一天没怎么说话"),
    ("你在干嘛", 0.4, 0.8, 0.1, 0.1, 0.2, "他在", "困"),
    ("你怎么了", 0.3, 0.1, 0.8, 0.1, 0.3, "他在", "烦"),
    ("我回来了", 0.7, 0.1, 0.1, 0.1, 0.2, "他在", "他刚回来"),
    ("还难受吗", 0.4, 0.2, 0.2, 0.7, 0.2, "他在", "不舒服"),
    ("在吗", 0.5, 0.1, 0.1, 0.1, 0.5, "他在", "普通招呼"),
    ("睡不着", 0.2, 0.1, 0.6, 0.1, 0.6, "他有一阵没来了", "夜里"),
    ("陪我聊会", 0.6, 0.2, 0.2, 0.2, 0.3, "他在", "想说话"),
    ("一天没消息了", 0.1, 0.2, 0.2, 0.1, 0.9, "他有一阵没来了", "他没来"),
    ("刚醒啊", 0.5, 0.7, 0.2, 0.1, 0.2, "他在", "刚醒"),
    ("不想动", 0.3, 0.1, 0.7, 0.1, 0.3, "他在", "不想动"),
]


def main():
    rng = random.Random(77)
    rows = []
    for text, e, s, a, i, l, presence, scene in ITEMS:
        b = model.Body()
        b.e, b.s, b.a, b.i, b.l = e, s, a, i, l
        af = affect.infer(b, text, presence)
        # A：直接说（也是她会说的话）
        parts = []
        if e < 0.35:
            parts.append("有点累")
        if s > 0.6:
            parts.append("困")
        if a > 0.55:
            parts.append("有点烦")
        if l > 0.6:
            parts.append("有点闷")
        if i > 0.5:
            parts.append("不太舒服")
        a_line = "，".join(parts) + "。" if parts else "还行吧。"
        b_line = es.render(af) or "还行吧。"
        pair = [("A", a_line), ("B", b_line)]
        rng.shuffle(pair)
        rows.append(dict(scene=scene, state="、".join(parts) or "还行",
                         his=text, first=pair[0], second=pair[1]))
    md = ["# 她会怎么答（12 题）", "",
          "每题：他说一句话，下面是两种可能的回答。**选更像她本人会说的**。", ""]
    for i, r in enumerate(rows, 1):
        md.append("%d. 他说：%s（她当时：%s）" % (i, r["his"], r["state"]))
        md.append("   1) %s" % r["first"][1])
        md.append("   2) %s" % r["second"][1])
    md.append("")
    md.append("回复：1:1 2:2 … 12:1")
    open("evidence/p3/affect_blind_dialog.md", "w", encoding="utf-8").write("\n".join(md))
    json.dump(rows, open("evidence/p3/affect_blind_dialog.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("rows", len(rows))


if __name__ == "__main__":
    main()
