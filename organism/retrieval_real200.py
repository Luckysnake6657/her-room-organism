# -*- coding: utf-8 -*-
"""检索 200 条改写查询 + 50 条本子外问题；保存每条的 top5，供人工标注。"""
import difflib
import json
import random
import re

import numpy as np

from organism import api_client, notebook, retrieval
from organism.retrieval_real import rewrite_robust

NEG_PROMPT = """写 50 条中文口语问题，问的是一个人生活里可能有、但**下面这些事实里没有**的细节。
只输出 JSON 数组，每条一句。已有事实：
"""


def make_negatives(nb, n=50):
    texts = [e["text"] for e in nb.live()[:30]]
    body = "\n".join("- " + t[:80] for t in texts)
    raw = api_client.chat(NEG_PROMPT, body, max_tokens=3000, temperature=0.4)
    m = re.search(r"\[.*\]", raw, re.S)
    if not m:
        return []
    try:
        arr = json.loads(m.group(0))
    except Exception:
        return []
    return [str(x) for x in arr][:n]


def main():
    nb = notebook.Notebook("evidence/p3/cmw_import/notebook.json")
    rng = random.Random(20261029)
    sample = rng.sample(nb.live(), 200)
    qs = rewrite_robust([e["text"] for e in sample])
    hits, rrs, rows = [], [], []
    for e, q in zip(sample, qs):
        got = retrieval.retrieve(nb, q, k=5) if q else []
        texts = [x["text"] for _, x in got]
        ids = [x["id"] for _, x in got]
        soft = any(difflib.SequenceMatcher(None, e["text"], t).ratio() > 0.75 for t in texts)
        hit = e["id"] in ids or soft
        hits.append(1 if hit else 0)
        rrs.append((1.0 / (ids.index(e["id"]) + 1)) if e["id"] in ids else (0.5 if soft else 0.0))
        rows.append(dict(id=e["id"], query=q, expected=e["text"], top=texts))
    negs = make_negatives(nb, 50)
    neg_hits = sum(1 for q in negs if retrieval.retrieve(nb, q, k=3))
    r = random.Random(5)
    bs = [np.mean([r.choice(hits) for _ in hits]) for _ in range(2000)]
    out = dict(n=len(sample), recall5=float(np.mean(hits)),
               recall_ci=(float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))),
               mrr=float(np.mean(rrs)), neg_hits=neg_hits, neg_total=len(negs),
               rows=rows)
    json.dump(out, open("evidence/p3/retrieval_real200.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(dict(n=out["n"], recall5=round(out["recall5"], 3),
                          ci=[round(x, 3) for x in out["recall_ci"]],
                          mrr=round(out["mrr"], 3),
                          neg=f"{neg_hits}/{len(negs)}"), ensure_ascii=False))


if __name__ == "__main__":
    main()
