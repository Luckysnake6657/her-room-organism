# -*- coding: utf-8 -*-
"""公平影子：同一候选池（放宽阈值）下，字面 top3 vs LLM 重排 top3。"""
import datetime as dt
import json
import re

from . import api_client, notebook, retrieval
from .rerank_shadow import JUDGE, PICK, queries, show

OUT = "evidence/p3/rerank_fair.jsonl"
POOL = dict(k=10, min_rel=0.2, min_score=0.0)


def main(n=140):
    nb = notebook.Notebook("evidence/p3/cmw_import/notebook.json")
    qs = queries(n)
    for qi, q in enumerate(qs, 1):
        cand = retrieval.retrieve(nb, q, **POOL)
        texts = [x["text"] for _, x in cand]
        lit = texts[:3]
        picked = []
        try:
            raw = api_client.chat(PICK % (q, show(texts, 10)), "",
                                  max_tokens=1500, temperature=0.0)
            if "none" not in raw.lower():
                for tok in re.findall(r"\d+", raw):
                    i = int(tok) - 1
                    if 0 <= i < len(texts):
                        picked.append(texts[i])
                picked = picked[:3]
        except Exception:
            picked = lit
        j = "tie"
        try:
            j = api_client.chat(JUDGE % (q, show(lit), show(picked or ["（空）"])), "",
                                max_tokens=800, temperature=0.0).strip().lower()
            j = "a" if j.startswith("a") else ("b" if j.startswith("b") else "tie")
        except Exception:
            pass
        row = dict(i=qi, q=q, pool=len(texts), lit=lit, rerank=picked, judge=j,
                   t=dt.datetime.now().isoformat())
        with open(OUT, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(qi, n, j, flush=True)


if __name__ == "__main__":
    main()
