# -*- coding: utf-8 -*-
"""把已核实的影子事实改写成完整命题，加入影子本子。"""
import json

from . import notebook

CANON = [
    "他的手机是华为 P70。",
    "他搜过 AIGC、LLM、Agent 相关内容。",
    "他在 Stable Diffusion 刚推出时用过它。",
    "他给她发过小说文件。",
    "他想拉小5金哲一起去。",
    "他面临考研还是找工作的选择。",
    "他在 S25 赛季打了零场。",
    "他历史一共打了 295 场。",
    "他在 S24 的最高分是 1790。",
    "他的 Rating 是 1.14。",
    "他的 KD 是 1.23。",
    "他的胜率是 51%。",
    "他说话句子短、多语气词。",
]


def main():
    nb = notebook.Notebook("evidence/p3/shadow_userfacts/notebook.json")
    seen = {e["text"] for e in nb.entries}
    n = 0
    for t in CANON:
        if t in seen:
            continue
        nb.add(t, type="fact", source="canonical", confidence=0.8)
        n += 1
    print("added", n, "total", len(nb.entries))


if __name__ == "__main__":
    main()
