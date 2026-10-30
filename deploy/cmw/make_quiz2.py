# -*- coding: utf-8 -*-
import json
import random

rows = json.load(open("evidence/p3/shadow_c3/pairs.json", encoding="utf-8"))
used = {(r["ours"], r["hers"]) for r in json.load(open("evidence/p3/shadow_c3/pairs.json", encoding="utf-8"))[:0]}
# 排除第一轮已用过的对（按文本比对）
r1 = open("evidence/p3/human_quiz.md", encoding="utf-8").read()
pool = [r for r in rows if r["ours"] not in r1 or r["hers"] not in r1]
rng = random.Random(20261028)
sample = rng.sample(pool, 10)
lines = ["# 人工盲评 第二轮", ""]
key = {}
for n, r in enumerate(sample, 1):
    swap = rng.random() < 0.5
    a, b = (r["ours"], r["hers"]) if swap else (r["hers"], r["ours"])
    key[str(n)] = "A" if swap else "B"
    lines += ["## 第 %d 对" % n, "A：%s" % a, "B：%s" % b, ""]
open("evidence/p3/human_quiz2.md", "w", encoding="utf-8").write("\n".join(lines))
json.dump(key, open("evidence/p3/human_key2.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("done", len(sample))
