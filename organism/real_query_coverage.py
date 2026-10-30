# -*- coding: utf-8 -*-
"""真实问句的检索覆盖率：她的本子 vs 影子本子。"""
import json
import re

from . import notebook, retrieval

QMARK = re.compile(r"吗|呢|什么|哪|多少|怎么|是不是|有没有|几点|谁")


def main():
    nb = notebook.Notebook("evidence/p3/cmw_import/notebook.json")
    sh = notebook.Notebook("evidence/p3/shadow_userfacts/notebook.json")
    qs = []
    for line in open("evidence/p3/cmw_messages/messages.jsonl", encoding="utf-8"):
        d = json.loads(line)
        if d.get("isSelf") or not d.get("isOwner"):
            continue
        t = re.sub(r"\[[^\]]*\]", "", d.get("text") or "").strip()
        if 4 <= len(t) <= 40 and (QMARK.search(t) or t.endswith("？")):
            qs.append(t)
    seen = []
    for q in qs:
        if q not in seen:
            seen.append(q)
    qs = seen[:100]
    out = dict(n=len(qs), her_hit=0, shadow_hit=0, her_only=0, shadow_only=0)
    for q in qs:
        h = retrieval.retrieve(nb, q, k=3, min_rel=0.3, min_score=0.0)
        s = retrieval.retrieve(sh, q, k=3, min_rel=0.3, min_score=0.0)
        out["her_hit"] += bool(h)
        out["shadow_hit"] += bool(s)
        out["her_only"] += bool(h) and not s
        out["shadow_only"] += bool(s) and not h
    json.dump(out, open("evidence/p3/real_query_coverage.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
