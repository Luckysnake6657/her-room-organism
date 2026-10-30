# -*- coding: utf-8 -*-
"""第六轮：新语境 20 对，B 同上一轮（cap 24），用于与第五轮合并 40 对。"""
import json
import random

from . import renderer_b as R, api_client

A_BASE = """你是她。说话短、口语化，不用表情，像 QQ 聊天。
【他刚说】%s
【你现在】%s
只回一句。"""

STATES = ["还行", "有点累", "有点困", "心里有点烦", "心情不错", "刚醒，还有点懵",
          "有点饿", "还行，就是不想动", "有点闷", "挺平静的",
          "有点忙", "没什么精神", "还好", "有点烦但不想说", "刚忙完",
          "有点冷", "犯困", "还行吧", "有点急躁", "松下来了"]


def main():
    prof = R.load_profile()
    lines = R.load_lines()
    msgs = [json.loads(l)["text"] for l in open("evidence/p3/cmw_messages/messages.jsonl", encoding="utf-8")
            if not json.loads(l).get("isSelf") and json.loads(l).get("isOwner")]
    msgs = [m.strip() for m in msgs if 6 <= len(m.strip()) <= 40]
    contexts = msgs[50:70]
    rng = random.Random(33)
    rows = []
    for idx, c in enumerate(contexts):
        st = STATES[idx % len(STATES)]
        try:
            a = api_client.chat(A_BASE % (c, st), c, max_tokens=800,
                                temperature=0.8).strip()
        except Exception:
            a = ""
        ex = R.exemplars(c, lines)
        prompt = R.build_prompt(prof, st, [], ex, c, max_chars=24)
        try:
            b = api_client.chat(prompt, c, max_tokens=800, temperature=0.8).strip()
        except Exception:
            b = ""
        if not a or not b:
            continue
        pair = [("A", a), ("B", b)]
        rng.shuffle(pair)
        rows.append(dict(context=c, state=st, first=pair[0], second=pair[1]))
    md = ["# 像不像她：第六轮（合并用，新语境 20 对）", ""]
    for i, r in enumerate(rows, 1):
        md.append("%d. 他说：%s（她当时：%s）" % (i, r["context"], r["state"]))
        md.append("   1) %s" % r["first"][1])
        md.append("   2) %s" % r["second"][1])
    md.append("")
    md.append("回复格式：1:1 2:2 … %d:1" % len(rows))
    open("evidence/p3/persona_blind6.md", "w", encoding="utf-8").write("\n".join(md))
    json.dump(rows, open("evidence/p3/persona_blind6.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("rows", len(rows))


if __name__ == "__main__":
    main()
