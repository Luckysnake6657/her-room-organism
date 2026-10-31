# -*- coding: utf-8 -*-
"""元认知硬指标：type-2 ROC 的 meta-d' 与 M-ratio（近似实现）。

- d1：单区间无偏估计 d1 = 2*z(accuracy)
- meta-d'：置信当 type-2 评分，type-2 ROC AUC → d' = sqrt(2)*z(AUC)
- M-ratio = meta-d' / d1
对照：打乱置信与对错 200 次，meta-d' 应≈0。

文献：Maniscalco & Lau 2012；Fleming & Lau 2014。
"""
import json

import numpy as np
from scipy.stats import norm
from sklearn.metrics import roc_auc_score

from . import metacog_eval as ME
from . import notebook, retrieval


def meta_d(scores, labels):
    s = np.asarray(scores, float)
    y = np.asarray(labels, float)
    if len(set(y)) < 2:
        return 0.0, 0.5
    auc2 = roc_auc_score(y, s)
    return float(np.sqrt(2) * norm.ppf(max(1e-6, min(1 - 1e-6, auc2)))), float(auc2)


def main():
    nb = notebook.Notebook("evidence/p3/cmw_native/notebook.json")
    items = json.load(open("evidence/p3/quiz100_data.json", encoding="utf-8"))
    scores, exact, any3 = [], [], []
    for it in items:
        if it.get("gold") is None:
            continue
        got = retrieval.retrieve(nb, it["q"], k=5, min_rel=0.0, min_score=0.0)
        if not got:
            scores.append(0.0)
            exact.append(0)
            any3.append(0)
            continue
        scores.append(float(got[0][0]))
        exact.append(1 if ME.m(got[0][1]["text"], it["gold"]) else 0)
        any3.append(1 if any(ME.m(e["text"], it["gold"]) for _, e in got[:3]) else 0)

    def evaluate(labels):
        acc = float(np.mean(labels))
        d1 = float(2 * norm.ppf(max(1e-6, min(1 - 1e-6, acc))))
        md, auc2 = meta_d(scores, labels)
        rng = np.random.default_rng(0)
        perm = [meta_d(scores, rng.permutation(labels))[0] for _ in range(200)]
        lo, hi = np.percentile(perm, [2.5, 97.5])
        return dict(n=len(scores), acc=round(acc, 3), d1=round(d1, 3),
                    auc2=round(auc2, 3), meta_d=round(md, 3),
                    m_ratio=round(md / d1, 3) if d1 else None,
                    perm_ci=[round(float(lo), 3), round(float(hi), 3)])

    out = dict(exact_top1=evaluate(exact), any_top3=evaluate(any3))
    json.dump(out, open("evidence/p3/metacog_proof.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
