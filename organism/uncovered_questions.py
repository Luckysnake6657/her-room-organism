# -*- coding: utf-8 -*-
"""拆解真实问句里"检索为空"的那些：是没内容，还是内容在但没够阈值。"""
import json
import re

from . import notebook, retrieval

QMARK = re.compile(r"吗|呢|什么|哪|多少|怎么|是不是|有没有|几点|谁")


def main():
    nb = notebook.Notebook("evidence/p3/cmw_import/notebook.json")
    texts = [e["text"] for e in nb.live()]
    qs = []
    for line in open("evidence/p3/cmw_messages/messages.jsonl", encoding="utf-8"):
        d = json.loads(line)
        if d.get("isSelf") or not d.get("isOwner"):
            continue
        t = re.sub(r"\[[^\]]*\]", "", d.get("text") or "").strip()
        if 4 <= len(t) <= 40 and (QMARK.search(t) or t.endswith("？")):
            if t not in qs:
                qs.append(t)
    qs = qs[:100]
    rows = []
    for q in qs:
        got = retrieval.retrieve(nb, q, k=3, min_rel=0.3, min_score=0.0)
        if got:
            continue
        grams = set(retrieval._bigrams(q))
        has = sum(1 for t in texts if grams & set(retrieval._bigrams(t)))
        rows.append(dict(q=q, entries_with_shared_bigram=has))
    rows.sort(key=lambda r: -r["entries_with_shared_bigram"])
    json.dump(rows, open("evidence/p3/uncovered_questions.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("uncovered", len(rows),
          "with_content", sum(1 for r in rows if r["entries_with_shared_bigram"] > 0),
          "no_content", sum(1 for r in rows if r["entries_with_shared_bigram"] == 0))


if __name__ == "__main__":
    main()
