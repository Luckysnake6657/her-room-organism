# -*- coding: utf-8 -*-
"""纠错闭环量化：20 条记忆各纠正一次，检查是否还会断言。"""
import json
import os
import tempfile

from . import memory_policy, notebook

out = []
d = tempfile.mkdtemp()
p = os.path.join(d, "nb.json")
json.dump({"next": 1, "entries": []}, open(p, "w", encoding="utf-8"))
nb = notebook.Notebook(p)
for i in range(20):
    e = nb.add("第 %d 条事实：周%d 要去医院。" % (i + 1, i % 7 + 1),
               type="fact", confidence=0.95)
    nb.record_outcome(e, False)
    band = memory_policy.band([(0.99, e)])
    out.append(dict(i=i + 1, contested=bool(e.get("contested")), band=band,
                    assert_ok=band != "assert"))
rate = sum(1 for x in out if x["assert_ok"]) / len(out)
json.dump(dict(n=len(out), never_assert=rate, rows=out),
          open("evidence/p3/correction_eval.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print("never_assert", rate)
