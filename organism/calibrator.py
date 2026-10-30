# -*- coding: utf-8 -*-
"""presence 校准器：特征 + logistic，输出概率（影子用）。"""
import json
import math

FEATS = ["score", "margin", "n", "coverage", "qlen", "tlen", "user_src"]


def _feat(scored, q):
    if not scored:
        return [0.0, 0.0, 0.0, 0.0, len(q), 0.0, 0.0]
    from . import retrieval
    top = scored[0]
    margin = top[0] - (scored[1][0] if len(scored) > 1 else 0.0)
    return [top[0], margin, len(scored),
            retrieval._bigram_rel(q, top[1]["text"]), len(q),
            len(top[1]["text"]),
            1.0 if top[1].get("source") == "user_confirmed" else 0.0]


class Calibrator:
    def __init__(self, path="evidence/p3/calibrator.json"):
        d = json.load(open(path, encoding="utf-8"))
        self.w = d["weights"]
        self.b = d["bias"]
        self.mu = d["mu"]
        self.sd = d["sd"]

    def p(self, scored, q):
        x = _feat(scored, q)
        z = self.b + sum(w * (v - m) / (s or 1.0)
                         for w, v, m, s in zip(self.w, x, self.mu, self.sd))
        return 1.0 / (1.0 + math.exp(-z))
