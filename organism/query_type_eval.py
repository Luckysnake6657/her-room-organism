# -*- coding: utf-8 -*-
"""按查询类型分层：模板兜底 vs 模型改写，自动指标差多少。"""
import json

from . import notebook, retrieval

rows = json.load(open("evidence/p3/retrieval_real200.json", encoding="utf-8"))["rows"]
nb = notebook.Notebook("evidence/p3/cmw_import/notebook.json")
buckets = {"template": [], "paraphrase": []}
for r in rows:
    kind = "template" if r["query"].startswith("关于「") else "paraphrase"
    got = retrieval.retrieve(nb, r["query"], k=5, min_rel=0.2, min_score=0.0)
    top = [x["text"] for _, x in got]
    hit = any(t == r["expected"] for t in top)
    buckets[kind].append((hit, bool(top) and top[0] == r["expected"]))
for k, v in buckets.items():
    if v:
        print(k, "n", len(v), "recall5", round(sum(h for h, _ in v) / len(v), 3),
              "top1", round(sum(t for _, t in v) / len(v), 3))
