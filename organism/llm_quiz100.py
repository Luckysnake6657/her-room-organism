# -*- coding: utf-8 -*-
"""LLM 答 quiz100（同选项），作为人工的对照基线。"""
import json
import re

from . import api_client

P = """问：%s

候选：
%s
F. 都没记 / 不知道

选最能回答的一项，只输出 A-F 一个字母。"""


def main():
    key = json.load(open("evidence/p3/quiz100_key.json", encoding="utf-8"))
    items = json.load(open("evidence/p3/quiz100_data.json", encoding="utf-8"))
    out = {}
    for n in range(1, 101):
        k = key[str(n)]
        lines = []
        for j, oi in enumerate(k["order"]):
            lines.append("%s. %s" % ("ABCDE"[j], k["options"][oi][:90]))
        body = "\n".join(lines)
        try:
            raw = api_client.chat(P % (items[n - 1]["q"], body), "",
                                  max_tokens=800, temperature=0.0).strip()
        except Exception:
            raw = "F"
        m = re.search(r"[A-Fa-f]", raw)
        out[str(n)] = m.group(0).upper() if m else "F"
        if n % 10 == 0:
            print(n, flush=True)
    json.dump(out, open("evidence/p3/quiz100_llm.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("done")


if __name__ == "__main__":
    main()
