# -*- coding: utf-8 -*-
"""混合检索评估：基线 vs RRF，200 gold，三次重复。"""
import difflib
import json

from . import notebook, retrieval

NEG = ["我上周是不是说过要去看极光", "我的猫叫什么名字", "我什么时候说要换工作",
       "我对花生过敏吗", "我上次体检是哪天", "我借给谁钱了", "我的车停在哪",
       "我答应过谁什么", "我生日是哪天", "我在哪家公司上班"]


def hit(texts, exp):
    return any(difflib.SequenceMatcher(None, t, exp).ratio() > 0.85 for t in texts)


def run(nb, rows):
    from . import hybrid
    b1 = b5 = h1 = h5 = 0
    for r in rows:
        exp = r["expected"]
        base = [x["text"] for _, x in retrieval.retrieve(nb, r["query"], k=5,
                                                          min_rel=0.3, min_score=0.0)]
        hyb = [x["text"] for _, x in hybrid.retrieve(nb, r["query"], k=5)]
        b5 += hit(base, exp)
        h5 += hit(hyb, exp)
        b1 += bool(base) and difflib.SequenceMatcher(None, base[0], exp).ratio() > 0.85
        h1 += bool(hyb) and difflib.SequenceMatcher(None, hyb[0], exp).ratio() > 0.85
    nb_ = sum(len(hybrid.retrieve(nb, q, k=5)) for q in NEG)
    nb_base = sum(len(retrieval.retrieve(nb, q, k=5, min_rel=0.3, min_score=0.0)) for q in NEG)
    return dict(base_top1=b1, base_top5=b5, hyb_top1=h1, hyb_top5=h5,
                neg_base=nb_base, neg_hyb=nb_)


def main():
    nb = notebook.Notebook("evidence/p3/cmw_import/notebook.json")
    rows = json.load(open("evidence/p3/retrieval_real200.json", encoding="utf-8"))["rows"]
    n = len(rows)
    runs = [run(nb, rows) for _ in range(3)]
    avg = {k: round(sum(r[k] for r in runs) / 3 / (n if "top" in k else 1), 3)
           for k in runs[0]}
    json.dump(dict(n=n, runs=runs, avg=avg),
              open("evidence/p3/hybrid_eval.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(avg, ensure_ascii=False))


if __name__ == "__main__":
    main()
