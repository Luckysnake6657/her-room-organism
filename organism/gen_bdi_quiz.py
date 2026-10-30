# -*- coding: utf-8 -*-
"""生成 BDI 人工判卷数据：30 条消息 + 抽出的字段（不含置信分）。"""
import json
import random
import re

from . import bdi

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
    random.Random(2026).shuffle(msgs)
    items = []
    for m in msgs:
        if len(items) >= 30:
            break
        b = bdi.extract(m)
        fields = [(k, b[k], b["confs"].get(k, 0)) for k in bdi.FIELDS if b.get(k)]
        if len(fields) < 1:
            continue
        items.append(dict(msg=m, fields=[dict(k=k, text=t, conf=c) for k, t, c in fields]))
    json.dump(items, open("evidence/p3/bdi_quiz_data.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("items", len(items), "fields", sum(len(i["fields"]) for i in items))


if __name__ == "__main__":
    main()
