# -*- coding: utf-8 -*-
"""答案门控：严格检索为空时，用 bigram 覆盖率决定要不要捞。"""
import difflib
import json

from . import notebook, retrieval


def m(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio() > 0.85


def best_by_coverage(nb, q):
    qs = set(retrieval._bigrams(q))
    best, bc = None, 0.0
    for e in nb.live():
        cov = len(qs & set(retrieval._bigrams(e["text"]))) / (len(qs) or 1)
        if cov > bc:
            best, bc = e, cov
    return best, bc


def main():
    nb = notebook.Notebook("evidence/p3/cmw_import/notebook.json")
    items = json.load(open("evidence/p3/quiz100_data.json", encoding="utf-8"))
    out = []
    for gamma in (0.0, 0.1, 0.15, 0.2, 0.25, 0.3):
        hit = wrong = none = ab = 0
        for it in items:
            got = retrieval.retrieve(nb, it["q"], k=3, min_rel=0.3, min_score=0.0)
            if not got and gamma > 0:
                e, cov = best_by_coverage(nb, it["q"])
                if e is not None and cov >= gamma:
                    got = [(cov, e)]
            if not got:
                none += 1
                continue
            t = got[0][1]["text"]
            g = it.get("gold")
            if g is None:
                ab += 1
            elif m(t, g):
                hit += 1
            else:
                wrong += 1
        out.append(dict(gamma=gamma, hit=hit, wrong=wrong, none=none, absent_bad=ab))
    json.dump(out, open("evidence/p3/gate_eval.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    for r in out:
        print(r)


if __name__ == "__main__":
    main()
