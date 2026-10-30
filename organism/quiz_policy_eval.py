# -*- coding: utf-8 -*-
"""在 100 题上量化：接住率、自信错、没记；对比分层前后与重排开关。"""
import difflib
import json

from . import memory_policy, notebook, rerank, retrieval


def match(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio() > 0.85


def eval_policy(nb, items, use_rerank, banded):
    stats = dict(asserts=0, correct_asserts=0, wrong_asserts=0,
                 hedges=0, wrong_hedges=0, none=0, answerable=0)
    for it in items:
        gold = it.get("gold")
        got = (rerank.retrieve(nb, it["q"], k=1) if use_rerank
               else retrieval.retrieve(nb, it["q"], k=1, min_rel=0.3, min_score=0.0))
        if gold:
            stats["answerable"] += 1
        if not got:
            stats["none"] += 1
            continue
        text = got[0][1]["text"]
        ok = bool(gold) and match(text, gold)
        band = memory_policy.band(got) if banded else "assert"
        if band == "assert":
            stats["asserts"] += 1
            stats["correct_asserts"] += ok
            stats["wrong_asserts"] += (not ok)
        elif band == "hedge":
            stats["hedges"] += 1
            stats["wrong_hedges"] += (not ok)
        else:
            stats["none"] += 1
    n = len(items)
    return dict(
        hit=round(stats["correct_asserts"] / stats["answerable"], 3) if stats["answerable"] else 0,
        confident_wrong=round(stats["wrong_asserts"] / stats["asserts"], 3) if stats["asserts"] else 0,
        none_rate=round(stats["none"] / n, 3),
        asserts=stats["asserts"], hedges=stats["hedges"], none=stats["none"],
        wrong_asserts=stats["wrong_asserts"], wrong_hedges=stats["wrong_hedges"])


def main():
    nb = notebook.Notebook("evidence/p3/cmw_import/notebook.json")
    items = json.load(open("evidence/p3/quiz100_data.json", encoding="utf-8"))
    out = {}
    for name, ur, bd in (("plain_assert", False, False),
                         ("plain_banded", False, True),
                         ("rerank_assert", True, False),
                         ("rerank_banded", True, True)):
        out[name] = eval_policy(nb, items, ur, bd)
    json.dump(out, open("evidence/p3/quiz_policy_eval.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
