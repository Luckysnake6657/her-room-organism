# -*- coding: utf-8 -*-
"""概率校准：presence（有没有）/ correctness（对不对）分开拟合 isotonic。

方法：按问题分组交叉验证（GroupKFold），避免同题泄漏；报 ECE 前后与可靠性分箱。
文献：Kuleshov et al. 2018（calibration regression）；Guo et al. 2017。
"""
import json
import os
import random
import tempfile

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.model_selection import GroupKFold

from . import notebook, retrieval


def ece(probs, labels, bins=5):
    p, y = np.array(probs), np.array(labels)
    edges = np.linspace(0, 1, bins + 1)
    tot, rows = 0.0, []
    for i in range(bins):
        m = (p >= edges[i]) & (p < edges[i + 1] if i < bins - 1 else p <= edges[i + 1])
        if m.sum() == 0:
            continue
        conf, acc = p[m].mean(), y[m].mean()
        tot += m.sum() * abs(conf - acc)
        rows.append(dict(bin=[round(edges[i], 2), round(edges[i + 1], 2)],
                         n=int(m.sum()), conf=round(float(conf), 3),
                         acc=round(float(acc), 3)))
    return tot / len(p), rows


def load():
    nb = notebook.Notebook("evidence/p3/cmw_native/notebook.json")
    items = json.load(open("evidence/p3/quiz100_clean_data.json", encoding="utf-8"))
    by_fact = {}
    for it in items:
        if it.get("gold"):
            by_fact.setdefault(it["gold"], []).append(it["q"])
    facts = [e for e in nb.entries if e.get("source") == "user_confirmed"
             and e["status"] != "deleted" and e["text"] in by_fact]
    questions = [(q, e["text"]) for e in facts for q in by_fact[e["text"]]]
    return nb, nb.entries, facts, questions


def score_with(entries, qs):
    d = tempfile.mkdtemp()
    p = os.path.join(d, "nb.json")
    json.dump({"next": 100000, "entries": entries}, open(p, "w", encoding="utf-8"))
    nb = notebook.Notebook(p)
    out = []
    for q in qs:
        got = retrieval.retrieve(nb, q, k=5, min_rel=0.0, min_score=0.0)
        out.append(got[0][0] if got else 0.0)
    return out


def fit_cv(scores, labels, groups):
    scores, labels = np.array(scores), np.array(labels)
    pred = np.zeros_like(scores)
    gk = GroupKFold(n_splits=5)
    for tr, te in gk.split(scores, labels, groups):
        iso = IsotonicRegression(out_of_bounds="clip")
        iso.fit(scores[tr], labels[tr])
        pred[te] = iso.predict(scores[te])
    return pred


def main():
    nb, entries, facts, questions = load()
    qs = [q for q, _ in questions]
    groups = np.array([g for _, g in questions])
    # presence
    ps, pl = [], []
    for seed in range(10):
        r = random.Random(seed)
        held = set(r.sample([e["text"] for e in facts], len(facts) // 2))
        kept = [e for e in entries if e["text"] not in held]
        ps.extend(score_with(kept, qs))
        pl.extend([0 if g in held else 1 for _, g in questions])
    ps, pl = np.array(ps), np.array(pl)
    pgroups = np.tile(groups, 10)
    pred = fit_cv(ps, pl, pgroups)
    e0, rows0 = ece(ps, pl)
    e1, rows1 = ece(pred, pl)
    # correctness（全量本子）
    cs = score_with(entries, qs)
    cl = []
    for q, g in questions:
        got = retrieval.retrieve(nb, q, k=3, min_rel=0.0, min_score=0.0)
        cl.append(1 if got and any(e["text"] == g for _, e in got) else 0)
    cs, cl = np.array(cs), np.array(cl)
    cpred = fit_cv(cs, cl, groups)
    c0, _ = ece(cs, cl)
    c1, _ = ece(cpred, cl)
    out = dict(
        presence=dict(n=len(ps), ece_raw=round(float(e0), 3), ece_cal=round(float(e1), 3),
                      bins_raw=rows0, bins_cal=rows1),
        correctness=dict(n=len(cs), base_rate=round(float(np.mean(cl)), 3),
                         ece_raw=round(float(c0), 3), ece_cal=round(float(c1), 3)))
    json.dump(out, open("evidence/p3/calibration.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False)[:400])


if __name__ == "__main__":
    main()
