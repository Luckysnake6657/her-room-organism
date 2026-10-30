# -*- coding: utf-8 -*-
import json

labels = {"1":"task","2":"task","3":"task","4":"task","5":"task","6":"task","7":"task",
"8":"task","9":"task","10":"task","11":"life","12":"task","13":"life","14":"life",
"15":"life","16":"life","17":"life","18":"task","19":"task","20":"task","21":"task",
"22":"task","23":"life","24":"task","25":"life","26":"task","27":"life","28":"life",
"29":"life","30":"task"}

d = json.load(open("evidence/p3/mode_rule2.json", encoding="utf-8"))
rule, texts = d["rule"], d["texts"]
ok = 0
diffs = []
for i in range(len(texts)):
    r = rule[i]
    l = labels.get(str(i + 1), "?")
    if r == l:
        ok += 1
    else:
        diffs.append((i + 1, r, l))
print("n", len(texts), "agree", ok, "=", round(ok / len(texts), 2))
print("rule task", sum(1 for x in rule if x == "task"),
      "label task", sum(1 for x in labels.values() if x == "task"))
for x in diffs:
    print("DIFF", x[0], "rule", x[1], "label", x[2])
