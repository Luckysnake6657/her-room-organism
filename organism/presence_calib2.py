# -*- coding: utf-8 -*-
"""presence 校准改进：多特征 + 分组交叉验证。"""
import json
import os
import random
import tempfile

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score

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


def features(nb, q):
    got = retrieval.retrieve(nb, q, k=5, min_rel=0.0, min_score=0.0)
    if not got:
        return [0.0, 0.0, 0.0, 0.0, len(q), 0.0, 0.0]
    top = got[0]
    margin = top[0] - (got[1][0] if len(got) > 1 else 0.0)
    cov = retrieval._bigram_rel(q, top[1]["text"])
    return [top[0], margin, len(got), cov, len(q), len(top[1]["text"]),
            1.0 if top[1].get("source") == "user_confirmed" else 0.0]


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
    for seed in range(10):
        r = random.Random(seed)
        held = set(r.sample([e["text"] for e in facts], len(facts) // 2))
        kept = [e for e in nb.entries if e["text"] not in held]
        d = tempfile.mkdtemp()
        p = os.path.join(d, "nb.json")
        json.dump({"next": 100000, "entries": kept}, open(p, "w", encoding="utf-8"))
        sub = notebook.Notebook(p)
        for q, gold in qs:
            X.append(features(sub, q))
            y.append(0 if gold in held else 1)
            g.append(gold)
    X, y, g = np.array(X), np.array(y), np.array(g)
    out = {}
    for name, model in (("logistic", LogisticRegression(max_iter=1000)),
                        ("gbm", GradientBoostingClassifier(random_state=0))):
        pred = np.zeros(len(y))
        for tr, te in GroupKFold(n_splits=5).split(X, y, g):
            model.fit(X[tr], y[tr])
            pred[te] = model.predict_proba(X[te])[:, 1]
        iso = IsotonicRegression(out_of_bounds="clip")
        cal = np.zeros(len(y))
        for tr, te in GroupKFold(n_splits=5).split(X, y, g):
            iso.fit(pred[tr], y[tr])
            cal[te] = iso.predict(pred[te])
        out[name] = dict(n=len(y), auc=round(float(roc_auc_score(y, pred)), 3), ece_raw=round(float(ece(pred, y)), 3),
                         ece_cal=round(float(ece(cal, y)), 3))
    out["score_only"] = dict(
        n=len(y),
        ece_raw=round(float(ece(X[:, 0], y)), 3),
        ece_cal=round(float(ece(IsotonicRegression(out_of_bounds="clip")
                                .fit(X[:, 0], y).predict(X[:, 0]), y)), 3))
    json.dump(out, open("evidence/p3/presence_calib2.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
