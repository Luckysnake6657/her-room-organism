# -*- coding: utf-8 -*-
"""查询改写评估：原查询 / 只去填充 / 去填充+扩展；阈值 0.3，三次重复。"""
import difflib
import json

from . import notebook, query_rewrite, retrieval

NEG = ["我上周是不是说过要去看极光", "我的猫叫什么名字", "我什么时候说要换工作",
       "我对花生过敏吗", "我上次体检是哪天", "我借给谁钱了", "我的车停在哪",
       "我答应过谁什么", "我生日是哪天", "我在哪家公司上班"]


def hit(texts, exp):
    return any(difflib.SequenceMatcher(None, t, exp).ratio() > 0.85 for t in texts)


def run_once(nb, rows):
    c = dict(top1_o=0, top5_o=0, top1_c=0, top5_c=0, top1_r=0, top5_r=0)
    for r in rows:
        q, exp = r["query"], r["expected"]
        rw = query_rewrite.rewrite(q)
        variants = {"o": q, "c": rw["clean"], "r": rw["query"]}
        for key, query in variants.items():
            got = [x["text"] for _, x in retrieval.retrieve(nb, query, k=5,
                                                             min_rel=0.3, min_score=0.0)]
            c["top5_" + key] += hit(got, exp)
            c["top1_" + key] += bool(got) and difflib.SequenceMatcher(None, got[0], exp).ratio() > 0.85
    for key in ("o", "c", "r"):
        c["neg_" + key] = sum(len(retrieval.retrieve(nb, q if key == "o" else
                                                     (query_rewrite.rewrite(q)["clean"] if key == "c"
                                                      else query_rewrite.rewrite(q)["query"]),
                                                     k=5, min_rel=0.3, min_score=0.0)) for q in NEG)
    return c


def main():
    nb = notebook.Notebook("evidence/p3/cmw_import/notebook.json")
    rows = json.load(open("evidence/p3/retrieval_real200.json", encoding="utf-8"))["rows"]
    n = len(rows)
    runs = [run_once(nb, rows) for _ in range(3)]
    avg = {k: round(sum(r[k] for r in runs) / 3 / (n if k.startswith("top") else 1), 3)
           for k in runs[0]}
    out = dict(n=n, runs=runs, avg=avg)
    json.dump(out, open("evidence/p3/query_rewrite_eval.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(avg, ensure_ascii=False))


if __name__ == "__main__":
    main()
