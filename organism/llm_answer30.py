# -*- coding: utf-8 -*-
"""让 LLM 答同一份 30 题卷，和人工对比（同选项、同顺序）。"""
import json
import re

from . import api_client

P = """查询：%s

候选：
%s

哪一项最能回答查询？只输出一个字母 A-E；都答不上来输出 none。"""


def main():
    key = json.load(open("evidence/p3/human_review_30_key.json", encoding="utf-8"))
    rows = json.load(open("evidence/p3/retrieval_real200.json", encoding="utf-8"))["rows"]
    out = {}
    for n in range(1, 31):
        k = key[str(n)]
        top = rows[k["src"] - 1]["top"]
        body = "\n".join("%s. %s" % ("ABCDE"[j], top[o][:90])
                         for j, o in enumerate(k["order"]))
        try:
            raw = api_client.chat(P % (rows[k["src"] - 1]["query"], body), "",
                                  max_tokens=800, temperature=0.0).strip()
        except Exception:
            raw = "none"
        m = re.search(r"[A-Ea-e]", raw)
        out[str(n)] = m.group(0).upper() if m and "none" not in raw.lower() else "无"
    json.dump(out, open("evidence/p3/llm30_answers.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("done", len(out))


if __name__ == "__main__":
    main()
