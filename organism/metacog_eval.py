# -*- coding: utf-8 -*-
"""元认知敏感度：置信分能否预测答对（AUC）、校准（ECE/Brier）。

文献：Fleming & Lau 2014（AUC/meta-d'）；Guo et al. 2017（校准）。
"""
import difflib
import json

import numpy as np
from sklearn.metrics import roc_auc_score

from . import notebook, retrieval


def m(a, b):
    a, b = str(a), str(b)
    return a in b or b in a or difflib.SequenceMatcher(None, a, b).ratio() > 0.85


def ece(scores, labels, bins=5):
    s = np.array(scores, dtype=float)
    y = np.array(labels, dtype=float)
    edges = np.linspace(0, 1, bins + 1)
    tot = 0.0
    for i in range(bins):
        lo, hi = edges[i], edges[i + 1]
        mask = (s >= lo) & (s < hi if i < bins - 1 else s <= hi)
        if mask.sum() == 0:
            continue
        tot += mask.sum() * abs(s[mask].mean() - y[mask].mean())
    return tot / len(s)


def main():
    nb = notebook.Notebook("evidence/p3/cmw_native/notebook.json")
    items = json.load(open("evidence/p3/quiz50_clean_data.json", encoding="utf-8")) \
        if False else json.load(open("evidence/p3/quiz100_data.json", encoding="utf-8"))
    scores, labels, margins = [], [], []
    for it in items:
        if it.get("gold") is None:
            continue
        got = retrieval.retrieve(nb, it["q"], k=5, min_rel=0.0, min_score=0.0)
        if not got:
            scores.append(0.0)
            labels.append(0)
            margins.append(0.0)
            continue
        s = got[0][0]
        hit = any(m(e["text"], it["gold"]) for _, e in got[:3])
        scores.append(s)
        labels.append(1 if hit else 0)
        margins.append(s - (got[1][0] if len(got) > 1 else 0.0))
    auc = roc_auc_score(labels, scores) if len(set(labels)) > 1 else float("nan")
    out = dict(n=len(labels), base_rate=round(float(np.mean(labels)), 3),
               auc=round(float(auc), 3),
               ece=round(float(ece(scores, labels)), 3),
               brier=round(float(np.mean((np.array(scores) - np.array(labels)) ** 2)), 3))
    json.dump(out, open("evidence/p3/metacog_eval.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
