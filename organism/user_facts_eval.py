# -*- coding: utf-8 -*-
"""影子用户事实：检索自测（问句由事实改写，仅测管道）。"""
import difflib
import json
import re

from . import api_client, notebook, retrieval

P = "把这条事实改成一句口语提问，只输出问题，不要含答案："
NEG = ["我上周是不是说要去看极光", "我表弟叫什么", "我什么时候搬的家",
       "我的车停哪", "我手机号尾号多少", "我哪年毕业"]


def main():
    nb = notebook.Notebook("evidence/p3/shadow_userfacts/notebook.json")
    facts = [e["text"] for e in nb.live()]
    hit = 0
    rows = []
    for f in facts:
        for _ in range(2):
            try:
                q = api_client.chat(P + f, "", max_tokens=200, temperature=0.0).strip()
            except Exception:
                q = ""
            if q:
                break
        if not q:
            continue
        got = [x["text"] for _, x in retrieval.retrieve(nb, q, k=5, min_rel=0.3, min_score=0.0)]
        ok = any(difflib.SequenceMatcher(None, t, f).ratio() > 0.85 for t in got)
        hit += ok
        rows.append(dict(q=q, gold=f, ok=ok))
    neg_bad = sum(1 for q in NEG if retrieval.retrieve(nb, q, k=3, min_rel=0.3, min_score=0.0))
    out = dict(n=len(rows), hit=hit, recall=round(hit / len(rows), 3) if rows else 0,
               neg_bad=neg_bad, rows=rows)
    json.dump(out, open("evidence/p3/userfacts_eval.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps({k: out[k] for k in ("n", "hit", "recall", "neg_bad")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
