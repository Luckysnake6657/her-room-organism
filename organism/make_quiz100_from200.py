# -*- coding: utf-8 -*-
"""用 200 条真实查询组 100 题：80 有答案 + 20 本子外。"""
import json
import random

NEG = ["我上周是不是说过要去看极光", "我的猫叫什么名字", "我什么时候说要换工作",
       "我对花生过敏吗", "我上次体检是哪天", "我借给谁钱了", "我的车停在哪",
       "我答应过谁什么", "我生日是哪天", "我在哪家公司上班",
       "我上次去杭州住哪", "我表弟叫什么", "我什么时候搬的家", "我买的显示器多大",
       "我上次跑步跑了几公里", "我手机号尾号是多少", "我哪天请的假",
       "我体检报告放哪了", "我什么时候说要去北京", "我存的钱够买什么"]


def main():
    rows = json.load(open("evidence/p3/retrieval_real200.json", encoding="utf-8"))["rows"]
    rng = random.Random(20261030)
    sample = rng.sample(rows, 80)
    items = []
    for r in sample:
        opts = list(r["top"])[:5]
        if r["expected"] not in opts:
            opts[0] = r["expected"]
        items.append(dict(kind="answerable", q=r["query"], gold=r["expected"], options=opts))
    all_texts = [r["expected"] for r in rows]
    for q in NEG[:20]:
        items.append(dict(kind="absent", q=q, gold=None,
                          options=rng.sample(all_texts, 5)))
    rng.shuffle(items)
    json.dump(items, open("evidence/p3/quiz100_data.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("items", len(items), "answerable", sum(1 for i in items if i["kind"] == "answerable"))


if __name__ == "__main__":
    main()
