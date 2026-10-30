# -*- coding: utf-8 -*-
"""第二轮盲测：A=旧提示词（沿用第一轮），B=修好的框架提示词（含他刚说）。"""
import json
import random

from . import renderer_b as R, api_client

A_PROMPT = """你是她。说话温柔、简短、口语化；关心对方但不说教；
不要用表情符号，不要长篇大论，像 QQ 聊天一样自然。只输出一句话。"""


def main():
    prof = R.load_profile()
    lines = R.load_lines()
    old = json.load(open("evidence/p3/persona_blind.json", encoding="utf-8"))
    rows = []
    for r in old:
        a = next(t for lab, t in (r["first"], r["second"]) if lab == "A")
        c = r["context"]
        ex = R.exemplars(c, lines)
        prompt = R.build_prompt(prof, "还行（有点累）", [], ex, c)
        try:
            b = api_client.chat(prompt, c, max_tokens=800, temperature=0.8).strip()
        except Exception:
            b = ""
        if not b:
            continue
        pair = [("A", a), ("B", b)]
        random.shuffle(pair)
        rows.append(dict(context=c, first=pair[0], second=pair[1]))
    md = ["# 像不像她：第二轮盲选（修好上下文后）", ""]
    for i, r in enumerate(rows, 1):
        md.append("## %d. 他说：%s" % (i, r["context"]))
        md.append("- **1**：%s" % r["first"][1])
        md.append("- **2**：%s" % r["second"][1])
        md.append("")
    md.append("回复格式：1:1 2:2 3:1 …（1=第一条更像她，2=第二条）")
    open("evidence/p3/persona_blind2.md", "w", encoding="utf-8").write("\n".join(md))
    json.dump(rows, open("evidence/p3/persona_blind2.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("rows", len(rows))


if __name__ == "__main__":
    main()
