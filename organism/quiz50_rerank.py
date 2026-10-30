# -*- coding: utf-8 -*-
"""同一份 50 题：重排路径能答对几道。"""
import difflib
import json
import re

from . import notebook, rerank

src = open("deploy/cmw/make_quiz50_user.py", encoding="utf-8").read()
pairs = dict((g, q) for q, g in re.findall(r'\("([^"]+)", "([^"]+)"\)', src))
key = json.load(open("evidence/p3/quiz50_user_key.json", encoding="utf-8"))
nb = notebook.Notebook("evidence/p3/cmw_native/notebook.json")


def m(a, b):
    a, b = str(a), str(b)
    return a in b or b in a or difflib.SequenceMatcher(None, a, b).ratio() > 0.85


hit = none = n = 0
for k in key.values():
    if k["kind"] != "answerable":
        continue
    q = pairs.get(k["gold"])
    if not q:
        continue
    n += 1
    got = rerank.retrieve(nb, q, k=3)
    if not got:
        none += 1
        continue
    if any(m(e["text"], k["gold"]) for _, e in got):
        hit += 1
out = dict(n=n, hit=hit, none=none, hit_rate=round(hit / n, 3) if n else 0)
json.dump(out, open("evidence/p3/quiz50_rerank.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False))
