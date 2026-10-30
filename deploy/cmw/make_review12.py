# -*- coding: utf-8 -*-
import json

rows = [json.loads(l) for l in open("evidence/p3/bdi_real/pairs.jsonl", encoding="utf-8")]
blind = {b["i"]: b for b in json.load(open("evidence/p3/bdi_real/blind.json", encoding="utf-8"))}
pick = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22]
lines = ["# 盲评 12 对", ""]
for i in pick:
    r = rows[i]
    b = blind[i]
    lines += ["## %d" % i,
              "- 他：%s" % r["owner"],
              "- 她真实：%s" % r["hers"],
              "- A：%s" % b["A"],
              "- B：%s" % b["B"], ""]
open("evidence/p3/bdi_real/review12.md", "w", encoding="utf-8").write("\n".join(lines))
print("ok", len(pick))
