# -*- coding: utf-8 -*-
"""生成人工盲评：10 对，A/B 随机，key 单独存。"""
import json
import random

rows = json.load(open("evidence/p3/shadow_c3/pairs.json", encoding="utf-8"))
rng = random.Random(777)
sample = rng.sample(rows, 10)
lines = ["# 人工盲评：哪一段是她？", ""]
key = {}
for n, r in enumerate(sample, 1):
    swap = rng.random() < 0.5
    a, b = (r["ours"], r["hers"]) if swap else (r["hers"], r["ours"])
    key[str(n)] = "A" if swap else "B"
    lines += ["## 第 %d 对" % n, "A：%s" % a, "B：%s" % b, ""]
open("evidence/p3/human_quiz.md", "w", encoding="utf-8").write("\n".join(lines))
json.dump(key, open("evidence/p3/human_key.json", "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("done", len(sample))
