# -*- coding: utf-8 -*-
import os
import tempfile

from organism import notebook, retrieval

fd, p = tempfile.mkstemp(suffix=".json")
os.close(fd)
open(p, "w", encoding="utf-8").write('{"next":1,"entries":[]}')
nb = notebook.Notebook(p)
e = nb.add("我下周三复查", confidence=0.9)
for _ in range(10):
    nb.record_outcome(e, False)
print("calibrated", e["calibrated"])
print("retrieval hits", len(retrieval.retrieve(nb, "复查")))
nb2 = notebook.Notebook(p)
print("reload outcomes", len(nb2.outcomes), "cal", nb2.live()[0].get("calibrated"))
os.remove(p)
