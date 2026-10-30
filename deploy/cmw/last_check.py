# -*- coding: utf-8 -*-
import json

from organism.native import Native

texts = ["睡了吗", "有点烦", "这个东西进展有点不顺利", "框架结构吧", "我得多做做实验了"]
t0 = 1793194701865

s = json.load(open(r"D:\qq-bridge\state\social-v2.json", encoding="utf-8"))
msgs = s["conversations"]["private:owner"]["recentMessages"]
real = ""
started = False
for m in sorted(msgs, key=lambda x: float(x.get("time") or 0)):
    if float(m.get("time") or 0) == t0:
        started = True
        continue
    if started and m.get("isSelf"):
        real += str(m.get("text") or "")
    elif started:
        break

n = Native("evidence/p3/cmw_native", "evidence/p3/cmw_import", tick=False)
out = n.respond(texts, bdi=True)
lines = ["# 最新一条：BDI 修正后", "",
         "- 他：%s" % "；".join(texts),
         "- 她真实：%s" % real,
         "- BDI：%s" % json.dumps(out.get("bdi"), ensure_ascii=False),
         "- 草稿：%s" % out["text"]]
open("evidence/p3/last_check.md", "w", encoding="utf-8").write("\n".join(lines))
n.close()
print("done")
