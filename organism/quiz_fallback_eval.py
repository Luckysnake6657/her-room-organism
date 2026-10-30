# -*- coding: utf-8 -*-
"""为空兜底：字面不同阈值 vs BM25 兜底（确定性，无 LLM）。"""
import difflib
import json

from . import hybrid, notebook, retrieval


def m(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio() > 0.85


def run(nb, items, mode):
    hit = wrong = none_ans = absent_bad = 0
    for it in items:
        gold = it.get("gold")
        got = None
        if mode in ("th30", "th20", "bm25"):
            th = 0.3 if mode == "th30" else 0.2
            cand = retrieval.retrieve(nb, it["q"], k=10, min_rel=th, min_score=0.0)
            if mode == "bm25" and not cand:
                qset = set(hybrid._grams(it["q"]))
                for s, e in hybrid.bm25_scores(nb, it["q"])[:3]:
                    cov = len(qset & set(hybrid._grams(e["text"]))) / (len(qset) or 1)
                    if cov >= 0.5:
                        cand = [(s, e)]
                        break
            got = cand[0][1]["text"] if cand else None
        if gold is None:
            absent_bad += bool(got)
            continue
        if got is None:
            none_ans += 1
        elif m(got, gold):
            hit += 1
        else:
            wrong += 1
    return dict(hit=hit, wrong=wrong, none=none_ans, absent_bad=absent_bad)


def main():
    nb = notebook.Notebook("evidence/p3/cmw_import/notebook.json")
    items = json.load(open("evidence/p3/quiz100_data.json", encoding="utf-8"))
    out = {mode: [run(nb, items, mode) for _ in range(3)]
           for mode in ("th30", "th20", "bm25")}
    json.dump(out, open("evidence/p3/quiz_fallback_eval.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
