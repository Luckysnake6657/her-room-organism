# -*- coding: utf-8 -*-
"""混合检索：字面重叠 + BM25，RRF 融合。"""
import math
from collections import Counter

from . import retrieval

K1, B = 1.5, 0.75


def _grams(text):
    t = "".join(ch for ch in str(text) if ch.strip())
    return [t[i:i + 2] for i in range(max(0, len(t) - 1))] or [t]


def bm25_scores(nb, query):
    q = Counter(_grams(query))
    docs = [(e, Counter(_grams(e["text"]))) for e in nb.live()]
    n = len(docs)
    if not n:
        return []
    avg = sum(sum(d.values()) for _, d in docs) / n
    out = []
    for e, d in docs:
        dl = sum(d.values())
        s = 0.0
        for g, qf in q.items():
            f = d.get(g, 0)
            if not f:
                continue
            idf = math.log(1 + (n - f + 0.5) / (f + 0.5))
            s += idf * (f * (K1 + 1)) / (f + K1 * (1 - B + B * dl / (avg or 1)))
        if s > 0:
            out.append((s, e))
    return sorted(out, key=lambda x: -x[0])


def retrieve(nb, query, k=5):
    lit = retrieval.retrieve(nb, query, k=max(k, 10), min_rel=0.3, min_score=0.0)
    qset = set(_grams(query))
    bm_raw = bm25_scores(nb, query)
    top = bm_raw[0][0] if bm_raw else 0.0
    bm = []
    for s, e in bm_raw:
        if len(bm) >= max(k, 10):
            break
        cov = len(qset & set(_grams(e["text"]))) / (len(qset) or 1)
        if cov >= 0.5 and s >= 0.4 * top:
            bm.append((s, e))
    rrf = {}
    ent = {}
    for rank, (_, e) in enumerate(lit):
        rrf[e["id"]] = rrf.get(e["id"], 0) + 1.0 / (60 + rank)
        ent[e["id"]] = e
    for rank, (_, e) in enumerate(bm):
        rrf[e["id"]] = rrf.get(e["id"], 0) + 1.0 / (60 + rank)
        ent[e["id"]] = e
    order = sorted(rrf, key=lambda i: -rrf[i])[:k]
    return [(rrf[i], ent[i]) for i in order]
