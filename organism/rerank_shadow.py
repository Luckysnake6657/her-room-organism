# -*- coding: utf-8 -*-
"""一周影子：字面检索 vs LLM 重排，逐条独立评判，写 JSONL。

用法：python -m organism.rerank_shadow [--n 140]
不修改线上任何状态；只读本子。
"""
import argparse
import datetime as dt
import json
import os
import re
import time

from . import api_client, notebook, retrieval

STATE = r"D:\qq-bridge\state\social-v2.json"
OUT = "evidence/p3/rerank_shadow.jsonl"

PICK = """你在帮一个记忆系统挑候选。查询：%s

候选：
%s

挑出最多 3 条能回答查询的候选，按相关度排序；都不行就输出 none。
只输出编号，逗号分隔，例如 3,1；或 none。"""

JUDGE = """查询：%s

方案 A（字面检索）：
%s

方案 B（重排）：
%s

哪个更能回答查询？只输出 A、B 或 tie。"""


def queries(n):
    st = json.load(open(STATE, encoding="utf-8"))
    msgs = (st.get("conversations", {}).get("private:owner", {})
            .get("recentMessages") or [])
    out, seen = [], set()
    for m in sorted(msgs, key=lambda x: float(x.get("time") or 0), reverse=True):
        t = re.sub(r"\[[^\]]*\]", "", m.get("text") or "").strip()
        if m.get("isSelf") or len(t) < 4 or t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= n:
            break
    if len(out) < n:
        try:
            for line in open("evidence/p3/cmw_messages/messages.jsonl", encoding="utf-8"):
                d = json.loads(line)
                t = re.sub(r"\[[^\]]*\]", "", d.get("text") or "").strip()
                if d.get("isSelf") or not d.get("isOwner") or len(t) < 4 or t in seen:
                    continue
                seen.add(t)
                out.append(t)
                if len(out) >= n:
                    break
        except Exception:
            pass
    return out


def show(items, k=3):
    return "\n".join("%d. %s" % (i + 1, t[:100]) for i, t in enumerate(items[:k]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=140)
    args = ap.parse_args()
    nb = notebook.Notebook("evidence/p3/cmw_import/notebook.json")
    qs = queries(args.n)
    rows = []
    for qi, q in enumerate(qs, 1):
        lit = [x["text"] for _, x in retrieval.retrieve(nb, q, k=3)]
        cand = retrieval.retrieve(nb, q, k=10, min_rel=0.0, min_score=0.0)
        cand_text = [x["text"] for _, x in cand]
        picked = []
        try:
            raw = api_client.chat(PICK % (q, show(cand_text, 10)), "",
                                  max_tokens=1500, temperature=0.0)
            if "none" not in raw.lower():
                for tok in re.findall(r"\d+", raw):
                    i = int(tok) - 1
                    if 0 <= i < len(cand_text):
                        picked.append(cand_text[i])
                picked = picked[:3]
        except Exception as e:
            picked = lit
        j = "tie"
        try:
            j = api_client.chat(JUDGE % (q, show(lit), show(picked or ["（空）"])), "",
                                max_tokens=800, temperature=0.0).strip().lower()
            j = "a" if j.startswith("a") else ("b" if j.startswith("b") else "tie")
        except Exception:
            pass
        row = dict(i=qi, q=q, lit=lit, rerank=picked, judge=j, t=dt.datetime.now().isoformat())
        rows.append(row)
        with open(OUT, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(qi, len(qs), j, flush=True)
    a = sum(1 for r in rows if r["judge"] == "a")
    b = sum(1 for r in rows if r["judge"] == "b")
    print("done", len(rows), "A", a, "B", b, "tie", len(rows) - a - b)


if __name__ == "__main__":
    main()
