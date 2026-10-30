# -*- coding: utf-8 -*-
"""答案核验：top1 候选能不能回答查询；不能就弃权/对冲。

文献：Asai et al. 2023（Self-RAG：检索后自评相关性）。
"""
import difflib
import json

from . import api_client, notebook, retrieval

P = """查询：%s

候选：%s

这条候选能回答查询吗？只输出 yes 或 no。"""


def m(a, b):
    return difflib.SequenceMatcher(None, a, b).ratio() > 0.85


def main():
    nb = notebook.Notebook("evidence/p3/cmw_import/notebook.json")
    items = json.load(open("evidence/p3/quiz100_data.json", encoding="utf-8"))
    hit = wrong = none = ab = rejected = 0
    rows = []
    for it in items:
        got = retrieval.retrieve(nb, it["q"], k=1, min_rel=0.3, min_score=0.0)
        if not got:
            none += 1
            rows.append(dict(q=it["q"], verdict="none"))
            continue
        text = got[0][1]["text"]
        ok = False
        try:
            raw = api_client.chat(P % (it["q"], text[:200]), "", max_tokens=400,
                                  temperature=0.0).strip().lower()
            ok = raw.startswith("yes") or "yes" in raw[:10]
        except Exception:
            ok = True
        if not ok:
            rejected += 1
            rows.append(dict(q=it["q"], verdict="reject"))
            continue
        g = it.get("gold")
        if g is None:
            ab += 1
        elif m(text, g):
            hit += 1
        else:
            wrong += 1
        rows.append(dict(q=it["q"], verdict="accept", ok=(g is not None and m(text, g))))
    out = dict(hit=hit, wrong=wrong, none=none, absent_bad=ab, rejected=rejected,
               n=len(items), rows=rows)
    json.dump(out, open("evidence/p3/verifier_eval.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps({k: out[k] for k in ("hit", "wrong", "none", "absent_bad", "rejected")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
