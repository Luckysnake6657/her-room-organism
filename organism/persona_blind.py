# -*- coding: utf-8 -*-
"""P1 盲测：现行风格提示词(A) vs 最小提示词(B)，随机顺序给管理员选。"""
import json
import random

from . import api_client, renderer_b as R

A_PROMPT = """你是她。说话温柔、简短、口语化；关心对方但不说教；
不要用表情符号，不要长篇大论，像 QQ 聊天一样自然。只输出一句话。"""


def main():
    prof = R.load_profile()
    lines = R.load_lines()
    shadow = json.load(open("evidence/p3/persona_shadow.json", encoding="utf-8"))
    samples = [s for s in shadow["samples"] if s["out"]][:10]
    rows = []
    for s in samples:
        try:
            a = api_client.chat(A_PROMPT, s["context"], max_tokens=800, temperature=0.8).strip()
        except Exception:
            a = ""
        if not a:
            continue
        pair = [("A", a), ("B", s["out"])]
        random.shuffle(pair)
        rows.append(dict(context=s["context"], first=pair[0], second=pair[1]))
    md = ["# 像不像她：盲选（每条选更像她的那条）", ""]
    for i, r in enumerate(rows, 1):
        md.append("## %d. 他说：%s" % (i, r["context"]))
        md.append("- **1**：%s" % r["first"][1])
        md.append("- **2**：%s" % r["second"][1])
        md.append("")
    md.append("回复格式：1:1 2:2 3:1 …（1=选第一条，2=选第二条）")
    open("evidence/p3/persona_blind.md", "w", encoding="utf-8").write("\n".join(md))
    json.dump(rows, open("evidence/p3/persona_blind.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("rows", len(rows))


if __name__ == "__main__":
    main()
