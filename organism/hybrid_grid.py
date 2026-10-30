# -*- coding: utf-8 -*-
"""混合检索参数网格：覆盖率/分数比/权重。"""
import difflib
import json

from . import hybrid, notebook, retrieval

NEG = ["我上周是不是说过要去看极光", "我的猫叫什么名字", "我什么时候说要换工作",
       "我对花生过敏吗", "我上次体检是哪天", "我借给谁钱了", "我的车停在哪",
       "我答应过谁什么", "我生日是哪天", "我在哪家公司上班"]


def hit(texts, exp):
    return any(difflib.SequenceMatcher(None, t, exp).ratio() > 0.85 for t in texts)


def run(nb, rows, cov_min, ratio, w):
    b1 = b5 = 0
    for r in rows:
        exp = r["expected"]
        b = [x["text"] for _, x in retrieval.retrieve(nb, r["query"], k=5,
                                                       min_rel=0.3, min_score=0.0)]
        b5 += hit(b, exp)
        b1 += bool(b) and difflib.SequenceMatcher(None, b[0], exp).ratio() > 0.85
    # 复用 hybrid 的内部逻辑，换参数
    def hyb(q, k=5):
        lit = retrieval.retrieve(nb, q, k=10, min_rel=0.3, min_score=0.0)
        qset = set(hybrid._grams(q))
        raw = hybrid.bm25_scores(nb, q)
        top = raw[0][0] if raw else 0.0
        rrf, ent = {}, {}
        for rank, (_, e) in enumerate(lit):
            rrf[e["id"]] = rrf.get(e["id"], 0) + 1.0 / (60 + rank)
            ent[e["id"]] = e
        for rank, (s, e) in enumerate(raw[:10]):
            cv = len(qset & set(hybrid._grams(e["text"]))) / (len(qset) or 1)
            if cv >= cov_min and s >= ratio * top:
                rrf[e["id"]] = rrf.get(e["id"], 0) + w / (60 + rank)
                ent[e["id"]] = e
        return [ent[i] for i in sorted(rrf, key=lambda i: -rrf[i])[:k]]
    h1 = h5 = 0
    for r in rows:
        exp = r["expected"]
        g = [e["text"] for e in hyb(r["query"])]
        h5 += hit(g, exp)
        h1 += bool(g) and difflib.SequenceMatcher(None, g[0], exp).ratio() > 0.85
    neg = sum(len(hyb(q)) for q in NEG)
    return b1, b5, h1, h5, neg


def main():
    nb = notebook.Notebook("evidence/p3/cmw_import/notebook.json")
    rows = json.load(open("evidence/p3/retrieval_real200.json", encoding="utf-8"))["rows"]
    n = len(rows)
    best = []
    for cov in (0.6, 0.7, 0.8):
        for ratio in (0.4, 0.6, 0.8):
            for w in (0.5, 1.0):
                b1, b5, h1, h5, neg = run(nb, rows, cov, ratio, w)
                best.append(dict(cov=cov, ratio=ratio, w=w,
                                 top1=round(h1 / n, 3), top5=round(h5 / n, 3),
                                 neg=neg, base1=round(b1 / n, 3), base5=round(b5 / n, 3)))
    best.sort(key=lambda x: (-x["top1"], -x["top5"], x["neg"]))
    json.dump(best, open("evidence/p3/hybrid_grid.json", "w", encoding="utf-8"), indent=2)
    for r in best[:8]:
        print(r)


if __name__ == "__main__":
    main()
