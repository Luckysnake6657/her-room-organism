# -*- coding: utf-8 -*-
"""A/A 对照：两条都用现行提示词独立生成，测盲选本身的噪声/偏差。"""
import json
import random

from . import api_client

A_BASE = """你是她。说话短、口语化，不用表情，像 QQ 聊天。
【他刚说】%s
【你现在】%s
只回一句。"""

STATES = ["还行", "有点累", "有点困", "心里有点烦", "心情不错",
          "刚醒，还有点懵", "有点饿", "还行，就是不想动", "有点闷", "挺平静的"]


def main():
    msgs = [json.loads(l)["text"] for l in open("evidence/p3/cmw_messages/messages.jsonl", encoding="utf-8")
            if not json.loads(l).get("isSelf") and json.loads(l).get("isOwner")]
    msgs = [m.strip() for m in msgs if 6 <= len(m.strip()) <= 40]
    contexts = msgs[70:80]
    rng = random.Random(55)
    rows = []
    for idx, c in enumerate(contexts):
        st = STATES[idx % len(STATES)]
        try:
            x = api_client.chat(A_BASE % (c, st), c, max_tokens=800, temperature=0.8).strip()
            y = api_client.chat(A_BASE % (c, st), c, max_tokens=800, temperature=0.8).strip()
        except Exception:
            continue
        if not x or not y:
            continue
        pair = [("A1", x), ("A2", y)]
        rng.shuffle(pair)
        rows.append(dict(context=c, state=st, first=pair[0], second=pair[1]))
    md = ["# A/A 对照：两条都是现行提示词（选更像她的）", ""]
    for i, r in enumerate(rows, 1):
        md.append("%d. 他说：%s（她当时：%s）" % (i, r["context"], r["state"]))
        md.append("   1) %s" % r["first"][1])
        md.append("   2) %s" % r["second"][1])
    md.append("")
    md.append("回复格式：1:1 2:2 … %d:1" % len(rows))
    open("evidence/p3/persona_aa.md", "w", encoding="utf-8").write("\n".join(md))
    json.dump(rows, open("evidence/p3/persona_aa.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("rows", len(rows))


if __name__ == "__main__":
    main()
