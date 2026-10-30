# -*- coding: utf-8 -*-
import json
import re

rows = [json.loads(l) for l in open("evidence/p3/bdi_real/pairs.jsonl", encoding="utf-8")]
blind = {b["i"]: b for b in json.load(open("evidence/p3/bdi_real/blind.json", encoding="utf-8"))}
done = {3, 4, 7, 9, 10, 11, 12, 13, 14, 15, 16, 17}

def substantive(t):
    t = re.sub(r"\[[^\]]*\]", "", t).replace("；", "").strip()
    return len(t) >= 4

rest = [r for r in rows if r["i"] not in done and substantive(r["owner"]) and substantive(r["hers"])]
rest = rest[:15]
lines = ["# 盲评 剩余 %d 对" % len(rest), ""]
for r in rest:
    i = r["i"]; b = blind[i]
    lines += ["## %d" % i,
              "- 他：%s" % r["owner"],
              "- 她真实：%s" % r["hers"],
              "- A：%s" % b["A"],
              "- B：%s" % b["B"], ""]
open("evidence/p3/bdi_real/review_rest.md", "w", encoding="utf-8").write("\n".join(lines))
print("rest", [r["i"] for r in rest])
