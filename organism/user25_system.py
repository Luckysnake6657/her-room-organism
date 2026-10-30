# -*- coding: utf-8 -*-
"""同一份 25 题：她现在的本子 vs 影子本子，各自能答多少。"""
import difflib
import json
import random
import sys

from . import notebook, retrieval

sys.path.insert(0, "deploy/cmw")
import importlib.util
spec = importlib.util.spec_from_file_location("mk", "deploy/cmw/make_quiz_user25.py")
mk = importlib.util.module_from_spec(spec)
spec.loader.exec_module.__self__ if False else None
# 手动重建题目顺序（与生成脚本同 seed）
FACTS = [
    ("我用的是什么手机？", "华为 P70"), ("我工资大概多少？", "月薪约 1 万"),
    ("我工作是做什么的？", "toB，提成是大头"), ("我刚工作那半年是什么状态？", "硬扛"),
    ("我工作的保底是怎么来的？", "家里托的关系"), ("我现在在纠结什么？", "考研还是找工作"),
    ("我 S25 赛季打了几场？", "零场"), ("我历史一共打了多少场？", "295 场"),
    ("我 S24 最高多少分？", "1790"), ("我 Rating 多少？", "1.14"),
    ("我 KD 多少？", "1.23"), ("我胜率多少？", "51%"),
    ("我之前搜过哪些技术？", "AIGC、LLM、Agent"),
    ("我什么时候用过 Stable Diffusion？", "刚推出时"),
    ("我给你发过什么文件？", "小说文件"), ("我想拉谁一起去？", "小5金哲"),
    ("我说话有什么特点？", "句子短、多语气词"),
]
ABSENT = ["我猫叫什么名字？", "我生日是哪天？", "我车停在哪？", "我上次体检是哪天？",
          "我借给谁钱了？", "我表弟叫什么？", "我住在哪？", "我手机号尾号多少？"]
rng = random.Random(20261031)
items = [dict(kind="answerable", q=q, gold=a) for q, a in FACTS]
items += [dict(kind="absent", q=q, gold=None) for q in ABSENT]
rng.shuffle(items)


def m(a, b):
    a, b = str(a), str(b)
    return a in b or b in a or difflib.SequenceMatcher(None, a, b).ratio() > 0.85


def run(nb):
    hit = wrong = none = ab = 0
    for it in items:
        got = retrieval.retrieve(nb, it["q"], k=3, min_rel=0.3, min_score=0.0)
        if not got:
            none += 1
            continue
        texts = [g[1]["text"] for g in got]
        if it["gold"] is None:
            ab += 1
        elif any(m(t, it["gold"]) for t in texts):
            hit += 1
        else:
            wrong += 1
    return dict(hit=hit, wrong=wrong, none=none, absent_bad=ab)


her = notebook.Notebook("evidence/p3/cmw_import/notebook.json")
sh = notebook.Notebook("evidence/p3/shadow_userfacts/notebook.json")
out = dict(her=run(her), shadow=run(sh))
json.dump(out, open("evidence/p3/user25_system.json", "w", encoding="utf-8"),
          ensure_ascii=False, indent=2)
print(json.dumps(out, ensure_ascii=False))
