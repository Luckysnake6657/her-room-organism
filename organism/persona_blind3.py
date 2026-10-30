# -*- coding: utf-8 -*-
"""第三轮盲测：每条上下文配一个不同的状态，A/B 用同一状态。"""
import json
import random

from . import renderer_b as R, api_client

A_BASE = """你是她。说话短、口语化，不用表情，像 QQ 聊天。
【他刚说】%s
【你现在】%s
只回一句。"""

STATES = ["还行", "有点累", "有点困", "心里有点烦", "心情不错", "刚醒，还有点懵",
          "有点饿", "还行，就是不想动", "有点闷", "挺平静的"]


def main():
    prof = R.load_profile()
    lines = R.load_lines()
    old = json.load(open("evidence/p3/persona_blind.json", encoding="utf-8"))
    rng = random.Random(7)
    rows = []
    for idx, r in enumerate(old):
        c = r["context"]
        st = STATES[idx % len(STATES)]
        try:
            a = api_client.chat(A_BASE % (c, st), c, max_tokens=800,
                                temperature=0.8).strip()
        except Exception:
            a = ""
        ex = R.exemplars(c, lines)
        prompt = R.build_prompt(prof, st, [], ex, c)
        try:
            b = api_client.chat(prompt, c, max_tokens=800, temperature=0.8).strip()
        except Exception:
            b = ""
        if not a or not b:
            continue
        pair = [("A", a), ("B", b)]
        rng.shuffle(pair)
        rows.append(dict(context=c, state=st, first=pair[0], second=pair[1]))
    md = ["# 像不像她：第三轮（每条不同状态，A/B 同状态）", ""]
    for i, r in enumerate(rows, 1):
        md.append("## %d. 他说：%s（她当时：%s）" % (i, r["context"], r["state"]))
        md.append("- **1**：%s" % r["first"][1])
        md.append("- **2**：%s" % r["second"][1])
        md.append("")
    md.append("回复格式：1:1 2:2 3:1 …")
    open("evidence/p3/persona_blind3.md", "w", encoding="utf-8").write("\n".join(md))
    json.dump(rows, open("evidence/p3/persona_blind3.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("rows", len(rows))


if __name__ == "__main__":
    main()
