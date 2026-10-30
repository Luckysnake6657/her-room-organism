# -*- coding: utf-8 -*-
"""分差对冲：top1 与 top2 分数太接近时改对冲，测能否压自信错。"""
import difflib
import json

from . import notebook, retrieval


def m(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio() > 0.85


def main():
    nb = notebook.Notebook("evidence/p3/cmw_import/notebook.json")
    items = json.load(open("evidence/p3/quiz100_data.json", encoding="utf-8"))
    rows = []
    for it in items:
        got = retrieval.retrieve(nb, it["q"], k=5, min_rel=0.3, min_score=0.0)
        rows.append((it, got))
    out = []
    for delta in (0.0, 0.02, 0.05, 0.08, 0.12, 0.2):
        hit = wrong = none = hedge = 0
        absent_bad = 0
        for it, got in rows:
            gold = it.get("gold")
            if not got:
                none += 1
                continue
            margin = got[0][0] - (got[1][0] if len(got) > 1 else 0.0)
            if delta and margin < delta:
                hedge += 1
                continue
            text = got[0][1]["text"]
            if gold is None:
                absent_bad += 1
                continue
            if m(text, gold):
                hit += 1
            else:
                wrong += 1
        out.append(dict(delta=delta, hit=hit, wrong=wrong, none=none,
                        hedge=hedge, absent_bad=absent_bad))
    json.dump(out, open("evidence/p3/margin_eval.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    for r in out:
        print(r)


if __name__ == "__main__":
    main()
