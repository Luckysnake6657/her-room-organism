# -*- coding: utf-8 -*-
"""门控诊断：每类问题触发多少、放过/拦下、错在哪。"""
import json
import difflib

from . import answer_gate as G, notebook, retrieval


def m(a, b):
    a, b = str(a), str(b)
    return a in b or b in a or difflib.SequenceMatcher(None, a, b).ratio() > 0.85


def kind(q):
    if G.NAME_Q.search(q):
        return "name"
    if G.DATE_Q.search(q):
        return "date"
    if G.MONEY_Q.search(q):
        return "money"
    if G.PLACE_Q.search(q):
        return "place"
    if G.NUM_Q.search(q):
        return "num"
    return "none"


def main():
    nb = notebook.Notebook("evidence/p3/cmw_import/notebook.json")
    items = json.load(open("evidence/p3/quiz100_data.json", encoding="utf-8"))
    rows = []
    for it in items:
        got = retrieval.retrieve(nb, it["q"], k=1, min_rel=0.3, min_score=0.0)
        if not got:
            rows.append(dict(q=it["q"], kind=kind(it["q"]), gold=it.get("gold"),
                             got=None, passed=None, ok=None))
            continue
        t = got[0][1]["text"]
        passed = G.gate(it["q"], t)
        ok = m(t, it["gold"]) if it.get("gold") else None
        rows.append(dict(q=it["q"], kind=kind(it["q"]), gold=it.get("gold"),
                         got=t[:40], passed=passed, ok=ok))
    out = []
    for k in ("name", "date", "money", "place", "num", "none"):
        sub = [r for r in rows if r["kind"] == k]
        out.append(dict(
            kind=k, n=len(sub),
            answered=sum(1 for r in sub if r["got"]),
            blocked=sum(1 for r in sub if r["passed"] is False),
            blocked_hits=sum(1 for r in sub if r["passed"] is False and r["ok"]),
            blocked_absent=sum(1 for r in sub if r["passed"] is False and r["gold"] is None),
            passed_absent=sum(1 for r in sub if r["passed"] and r["gold"] is None),
        ))
    json.dump(dict(by_kind=out, rows=rows),
              open("evidence/p3/gate_diag.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
