# -*- coding: utf-8 -*-
import json

from organism.intent import decide_mode
from organism.model import Body
import re

rows = []
for line in open("evidence/p3/cmw_messages/messages.jsonl", encoding="utf-8"):
    d = json.loads(line)
    if not d.get("isSelf") and d.get("isOwner"):
        t = re.sub(r"\[[^\]]*\]", "", d.get("text") or "").strip()
        if 4 <= len(t) <= 60:
            rows.append(t)
seen, texts = set(), []
for t in rows:
    if t not in seen:
        seen.add(t)
        texts.append(t)
texts = texts[:30]
b = Body()
rule = [decide_mode(b, t) for t in texts]
open("evidence/p3/mode_items.md", "w", encoding="utf-8").write(
    "\n".join("%d. %s" % (i + 1, t) for i, t in enumerate(texts)))
json.dump(dict(texts=texts, rule=rule),
          open("evidence/p3/mode_rule.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("items", len(texts))
