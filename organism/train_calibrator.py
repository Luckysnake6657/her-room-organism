# -*- coding: utf-8 -*-
"""训练 presence 校准器并保存权重。"""
import json
import os
import random
import tempfile

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

from . import notebook, retrieval


def ece(p, y, bins=5):
    p, y = np.array(p), np.array(y)
    edges = np.linspace(0, 1, bins + 1)
    tot = 0.0
    for i in range(bins):
        m = (p >= edges[i]) & (p < edges[i + 1] if i < bins - 1 else p <= edges[i + 1])
        if m.sum():
            tot += m.sum() * abs(p[m].mean() - y[m].mean())
    return tot / len(p)


def feats(nb, q):
    got = retrieval.retrieve(nb, q, k=5, min_rel=0.0, min_score=0.0)
    if not got:
        return [0.0, 0.0, 0.0, 0.0, len(q), 0.0, 0.0]
    margin = got[0][0] - (got[1][0] if len(got) > 1 else 0.0)
    return [got[0][0], margin, len(got),
            retrieval._bigram_rel(q, got[0][1]["text"]), len(q),
            len(got[0][1]["text"]),
            1.0 if got[0][1].get("source") == "user_confirmed" else 0.0]


def main():
    nb = notebook.Notebook("evidence/p3/cmw_native/notebook.json")
    items = json.load(open("evidence/p3/quiz100_clean_data.json", encoding="utf-8"))
    by_fact = {}
    for it in items:
        if it.get("gold"):
            by_fact.setdefault(it["gold"], []).append(it["q"])
    facts = [e for e in nb.entries if e.get("source") == "user_confirmed"
             and e["status"] != "deleted" and e["text"] in by_fact]
    qs = [(q, e["text"]) for e in facts for q in by_fact[e["text"]]]
    X, y, g = [], [], []
    for seed in range(50):
        r = random.Random(seed)
        held = set(r.sample([e["text"] for e in facts], len(facts) // 2))
        kept = [e for e in nb.entries if e["text"] not in held]
        d = tempfile.mkdtemp()
        p = os.path.join(d, "nb.json")
        json.dump({"next": 100000, "entries": kept}, open(p, "w", encoding="utf-8"))
        sub = notebook.Notebook(p)
        for q, gold in qs:
            X.append(feats(sub, q))
            y.append(0 if gold in held else 1)
            g.append(gold)
    X, y, g = np.array(X), np.array(y), np.array(g)
    mu, sd = X.mean(axis=0), X.std(axis=0)
    sd[sd == 0] = 1.0
    Z = (X - mu) / sd
    pred = np.zeros(len(y))
    for tr, te in GroupKFold(n_splits=5).split(Z, y, g):
        m = LogisticRegression(max_iter=1000).fit(Z[tr], y[tr])
        pred[te] = m.predict_proba(Z[te])[:, 1]
    m = LogisticRegression(max_iter=1000).fit(Z, y)
    out = dict(weights=[float(w) for w in m.coef_[0]], bias=float(m.intercept_[0]),
               mu=[float(x) for x in mu], sd=[float(x) for x in sd],
               cv=dict(n=len(y), auc=round(float(roc_auc_score(y, pred)), 3),
                       ece=round(float(ece(pred, y)), 3),
                       base_rate=round(float(np.mean(y)), 3)))
    json.dump(out, open("evidence/p3/calibrator.json", "w", encoding="utf-8"), indent=2)
    print(json.dumps(out["cv"], ensure_ascii=False))


if __name__ == "__main__":
    main()
