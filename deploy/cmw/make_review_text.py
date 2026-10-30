# -*- coding: utf-8 -*-
import json
import re

rows = [json.loads(l) for l in open("evidence/p3/bdi_real/pairs.jsonl", encoding="utf-8")]
blind = {b["i"]: b for b in json.load(open("evidence/p3/bdi_real/blind.json", encoding="utf-8"))}

def substantive(t):
    t = re.sub(r"\[[^\]]*\]", "", t)
    t = t.replace("；", "").strip()
    return len(t) >= 4

keep = [r for r in rows if substantive(r["owner"]) and substantive(r["hers"])]
keep = keep[:12]
lines = ["# 盲评（仅纯文字消息）", ""]
for r in keep:
    i = r["i"]
    b = blind[i]
    lines += ["## %d" % i,
              "- 他：%s" % r["owner"],
              "- 她真实：%s" % r["hers"],
              "- A：%s" % b["A"],
              "- B：%s" % b["B"], ""]
open("evidence/p3/bdi_real/review_text.md", "w", encoding="utf-8").write("\n".join(lines))
print("kept", len(keep), [r["i"] for r in keep])
