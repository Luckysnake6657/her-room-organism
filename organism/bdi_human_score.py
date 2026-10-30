# -*- coding: utf-8 -*-
"""BDI 人工盲判评分：准确率 + 置信与人工标签的关系。"""
import json

import numpy as np
from sklearn.metrics import roc_auc_score

ANS = ["对", "错", "对", "对", "对", "对", "对", "对", "对", "对", "不确定", "对",
       "对", "错", "对", "对", "对", "对", "对", "对", "对", "对", "错", "错",
       "对", "对", "对", "对", "对", "对", "对", "对", "对", "对", "对", "不确定"]


def ece(p, y, bins=5):
    p, y = np.array(p), np.array(y)
    edges = np.linspace(0, 1, bins + 1)
    tot = 0.0
    for i in range(bins):
        m = (p >= edges[i]) & (p < edges[i + 1] if i < bins - 1 else p <= edges[i + 1])
        if m.sum():
            tot += m.sum() * abs(p[m].mean() - y[m].mean())
    return tot / len(p)


def main():
    items = json.load(open("evidence/p3/bdi_quiz_data.json", encoding="utf-8"))
    flat = [(it["msg"], f) for it in items for f in it["fields"]]
    assert len(flat) == len(ANS), (len(flat), len(ANS))
    rows = []
    for (msg, f), a in zip(flat, ANS):
        rows.append(dict(msg=msg, field=f["k"], text=f["text"],
                         conf=float(f["conf"]), human=a))
    decided = [r for r in rows if r["human"] in ("对", "错")]
    y = [1 if r["human"] == "对" else 0 for r in decided]
    s = [r["conf"] for r in decided]
    out = dict(n=len(rows), decided=len(decided),
               uncertain=sum(1 for r in rows if r["human"] == "不确定"),
               acc=round(sum(y) / len(y), 3),
               wrong=[dict(n=i + 1, field=r["field"], text=r["text"],
                           conf=r["conf"], msg=r["msg"])
                      for i, r in enumerate(rows)
                      if r["human"] == "错"],
               conf_mean_correct=round(float(np.mean([r["conf"] for r in decided if r["human"] == "对"])), 3),
               conf_mean_wrong=round(float(np.mean([r["conf"] for r in decided if r["human"] == "错"])), 3))
    if len(set(y)) > 1:
        out["auc"] = round(float(roc_auc_score(y, s)), 3)
        out["ece"] = round(float(ece(s, y)), 3)
    json.dump(out, open("evidence/p3/bdi_human.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps({k: out[k] for k in ("n", "decided", "uncertain", "acc",
                                          "conf_mean_correct", "conf_mean_wrong",
                                          "auc", "ece") if k in out}, ensure_ascii=False))
    for w in out["wrong"]:
        print("WRONG", w["n"], w["field"], w["conf"])


if __name__ == "__main__":
    main()
