# -*- coding: utf-8 -*-
"""同一份 50 题：她（检索）能答对几道。"""
import difflib
import json
import re

from . import notebook, retrieval

src = open("deploy/cmw/make_quiz50_user.py", encoding="utf-8").read()
pairs = dict((g, q) for q, g in re.findall(r'\("([^"]+)", "([^"]+)"\)', src))
key = json.load(open("evidence/p3/quiz50_user_key.json", encoding="utf-8"))
nb = notebook.Notebook("evidence/p3/cmw_native/notebook.json")


def m(a, b):
    a, b = str(a), str(b)
    return a in b or b in a or difflib.SequenceMatcher(None, a, b).ratio() > 0.85


hit = none = 0
n = 0
miss = []
for k in key.values():
    if k["kind"] != "answerable":
        continue
    q = pairs.get(k["gold"])
    if not q:
        continue
    n += 1
    got = retrieval.retrieve(nb, q, k=3, min_rel=0.3, min_score=0.0)
    if not got:
        none += 1
        miss.append((q, "none"))
        continue
    if any(m(e["text"], k["gold"]) for _, e in got):
        hit += 1
    else:
        miss.append((q, "wrong"))
out = dict(n=n, hit=hit, none=none, hit_rate=round(hit / n, 3) if n else 0, miss=miss)
json.dump(out, open("evidence/p3/quiz50_system.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print(json.dumps({k: out[k] for k in ("n", "hit", "none", "hit_rate")}, ensure_ascii=False))
