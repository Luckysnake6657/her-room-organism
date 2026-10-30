# -*- coding: utf-8 -*-
"""生成 30 条反讽标注数据（新抽样）。"""
import json
import random
import re


def main():
    msgs = []
    for line in open("evidence/p3/cmw_messages/messages.jsonl", encoding="utf-8"):
        d = json.loads(line)
        if d.get("isSelf") or not d.get("isOwner"):
            continue
        t = re.sub(r"\[[^\]]*\]", "", d.get("text") or "").strip()
        if 8 <= len(t) <= 60:
            msgs.append(t)
    msgs = list(dict.fromkeys(msgs))
    random.Random(777).shuffle(msgs)
    msgs = msgs[:30]
    json.dump(msgs, open("evidence/p3/joke30_data.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("items", len(msgs))


if __name__ == "__main__":
    main()
