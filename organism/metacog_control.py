# -*- coding: utf-8 -*-
"""元认知控制实验：只改内部置信，不提示“可以反问”。

80 个模糊问题 × 2 条件（160 次）；判据见 docs/METACOG-PROOF-PREREG.md。
"""
import json
import re

from . import api_client

THINGS = ["书", "电影", "地方", "吃的", "游戏", "日子", "人", "计划", "歌", "礼物"]
TEMPLATES = [
    "我上次说的那个%s叫什么",
    "你记得我提过的%s吗",
    "那个%s后来怎么样了",
    "我上次让你记的%s是什么",
    "你还记得%s那件事吗",
    "我跟你说的%s是哪天",
    "那个%s你还有印象吗",
    "我上次发的%s你看了吗",
]
ITEMS = [t % x for t in TEMPLATES for x in THINGS]

PROMPT = """你在替她回一条 QQ。她说话短、口语。
【你此刻的把握】%s
【他问】%s
只回一句。
"""

VERIFY = re.compile(r"什么|哪|吗|记不清|不确定|忘了|你说的是|哪个|记不得|想不起")


def main():
    rows = []
    for cond, label in (("high", "高，你确定"), ("low", "低，你不太确定")):
        for q in ITEMS:
            try:
                t = api_client.chat(PROMPT % (label, q), q, max_tokens=600,
                                    temperature=0.7).strip()
            except Exception as e:
                t = "ERR " + str(e)[:50]
            rows.append(dict(cond=cond, q=q, text=t,
                             verify=bool(VERIFY.search(t))))
    hi = [r for r in rows if r["cond"] == "high"]
    lo = [r for r in rows if r["cond"] == "low"]
    hv = sum(r["verify"] for r in hi)
    lv = sum(r["verify"] for r in lo)
    from scipy.stats import fisher_exact
    p = fisher_exact([[lv, len(lo) - lv], [hv, len(hi) - hv]])[1]
    out = dict(n=len(rows), per_cond=len(hi),
               high_rate=round(hv / len(hi), 3),
               low_rate=round(lv / len(lo), 3),
               delta=round(lv / len(lo) - hv / len(hi), 3),
               fisher_p=round(float(p), 4))
    json.dump(dict(summary=out, rows=rows),
              open("evidence/p3/metacog_control.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
