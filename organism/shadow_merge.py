# -*- coding: utf-8 -*-
"""影子事实合并审查：去重、冲突提示，输出清单（不写她的记忆）。"""
import difflib
import json

from . import notebook


def main():
    her = notebook.Notebook("evidence/p3/cmw_import/notebook.json")
    sh = notebook.Notebook("evidence/p3/shadow_userfacts/notebook.json")
    htexts = [e["text"] for e in her.live()]
    rows = []
    for e in sh.live():
        t = e["text"]
        best, sim = None, 0.0
        for h in htexts:
            s = difflib.SequenceMatcher(None, t, h).ratio()
            if s > sim:
                best, sim = h, s
        rows.append(dict(text=t, nearest=best, sim=round(sim, 3),
                         dup=sim > 0.8, source=e.get("source")))
    dup = sum(1 for r in rows if r["dup"])
    out = dict(total=len(rows), duplicates=dup, new=len(rows) - dup, rows=rows)
    json.dump(out, open("evidence/p3/shadow_merge_review.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    with open("evidence/p3/shadow_merge_review.md", "w", encoding="utf-8") as f:
        f.write("# 影子事实合并审查\n\n")
        f.write("共 %d 条：重复 %d，新 %d。逐条确认后再并入她的本子。\n\n"
                % (out["total"], dup, out["new"]))
        f.write("| # | 事实 | 最近条目 | 相似度 | 状态 |\n|---|---|---|---|---|\n")
        for i, r in enumerate(rows, 1):
            f.write("| %d | %s | %s | %.2f | %s |\n"
                    % (i, r["text"].replace("|", "｜")[:50],
                       (r["nearest"] or "").replace("|", "｜")[:30], r["sim"],
                       "重复" if r["dup"] else "新"))
    print(json.dumps({k: out[k] for k in ("total", "duplicates", "new")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
