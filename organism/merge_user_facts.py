# -*- coding: utf-8 -*-
"""把 13 条已确认的用户事实并入她的本子（先备份）。"""
import json
import os
import shutil
import sys
import time

from . import notebook

FACTS = [
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
SRC = sys.argv[1] if len(sys.argv) > 1 else "evidence/p3/cmw_import/notebook.json"


def main():
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bak = "evidence/p3/backup/notebook-before-merge-%s.json" % stamp
    os.makedirs(os.path.dirname(bak), exist_ok=True)
    shutil.copyfile(SRC, bak)
    nb = notebook.Notebook(SRC)
    seen = {e["text"] for e in nb.entries}
    added = 0
    for t in FACTS:
        if t in seen:
            continue
        nb.add(t, type="fact", source="user_confirmed", confidence=0.9,
               importance=0.7)
        seen.add(t)
        added += 1
    print("backup", bak, "added", added, "total", len(nb.entries))


if __name__ == "__main__":
    main()
