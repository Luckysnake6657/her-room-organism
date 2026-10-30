# -*- coding: utf-8 -*-
import json

labels = {"1":"life","2":"life","3":"life","4":"task","5":"life","6":"life","7":"life",
"8":"life","9":"task","10":"life","11":"life","12":"life","13":"life","14":"task",
"15":"task","16":"life","17":"life","18":"life","19":"life","20":"life","21":"task",
"22":"task","23":"life","24":"life","25":"task","26":"task","27":"life","28":"life",
"29":"life","30":"task"}

d = json.load(open("evidence/p3/mode_rule.json", encoding="utf-8"))
rule = d["rule"]
texts = d["texts"]
ok = 0
diffs = []
for i in range(len(texts)):
    r = rule[i]
    l = labels.get(str(i + 1), "?")
    if r == l:
        ok += 1
    else:
        diffs.append((i + 1, r, l, texts[i]))
print("n", len(texts), "agree", ok, "=", round(ok / len(texts), 2))
print("rule task:", sum(1 for x in rule if x == "task"),
      "label task:", sum(1 for x in labels.values() if x == "task"))
for d0 in diffs:
    print("DIFF", d0[0], "rule", d0[1], "label", d0[2])
json.dump(diffs, open("evidence/p3/mode_compare.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
