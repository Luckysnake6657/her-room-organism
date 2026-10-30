# -*- coding: utf-8 -*-
"""对照：真实回复 vs 影子草稿；顺带看生长。"""
import json
import os

STATE = r"D:\qq-bridge\state\social-v2.json"
DRAFTS = "evidence/p3/cmw_native/drafts.jsonl"
DATA = "evidence/p3/cmw_native"

s = json.load(open(STATE, encoding="utf-8"))
msgs = s["conversations"]["private:owner"].get("recentMessages", [])
msgs = [m for m in msgs if m.get("text")]
drafts = [json.loads(l) for l in open(DRAFTS, encoding="utf-8")]

lines = ["# 影子对照", "", "| 他说的 | 她真实回的 | native 草稿 |", "|---|---|---|"]
for d in drafts:
    if d["t"] == 1000:
        continue
    idx = None
    for i, m in enumerate(msgs):
        if m.get("isSelf"):
            continue
        if abs(float(m.get("time") or 0) - d["t"]) < 1:
            idx = i
            break
    real = ""
    if idx is not None:
        for m in msgs[idx + 1:]:
            if not m.get("isSelf"):
                break
            real += str(m.get("text") or "")
    lines.append("| %s | %s | %s |" % (d["text"], real, d["draft"]))

lines += ["", "## 生长", "",
          "- 本子条目：%d" % sum(1 for _ in open(os.path.join(DATA, "notebook.json"), encoding="utf-8")),
          "- pending：%d" % sum(1 for l in open(os.path.join(DATA, "notebook.json"), encoding="utf-8")
                               if '"status": "pending"' in l),
          "- 日记：%d 行" % (sum(1 for _ in open(os.path.join(DATA, "diary.md"), encoding="utf-8"))
                            if os.path.exists(os.path.join(DATA, "diary.md")) else 0)]
open("evidence/p3/shadow_compare.md", "w", encoding="utf-8").write("\n".join(lines))
print("wrote", len(drafts), "drafts")
