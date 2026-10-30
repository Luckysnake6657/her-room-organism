# -*- coding: utf-8 -*-
"""并入 15 条待确认（偏好/经历类）影子事实。"""
import os
import shutil
import sys
import time

from . import notebook

FACTS = [
    "他不需要对方向他汇报。",
    "他不需要对方什么都对他说。",
    "他希望对方真有事时再告诉他。",
    "如果对方难受，他会租云服务器。",
    "他帮对方打过某样东西。",
    "他称自己来就通关了。",
    "他有时会引用时间跨度较大的消息。",
    "他希望有结果后被告知。",
    "他认为群聊需要限制一下。",
    "他的薪资在 1 万上下，具体看底薪还是含提成。",
    "他做 toB 业务，收入大头在提成上。",
    "他前半年基本是硬扛。",
    "他之前提到过训练量。",
    "他说过“这是好事，你竞争对手只有一个”。",
    "他的保底是家里托的关系。",
]
SRC = sys.argv[1] if len(sys.argv) > 1 else "evidence/p3/cmw_native/notebook.json"


def main():
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bak = "evidence/p3/backup/notebook-before-merge-review-%s.json" % stamp
    os.makedirs(os.path.dirname(bak), exist_ok=True)
    shutil.copyfile(SRC, bak)
    nb = notebook.Notebook(SRC)
    seen = {e["text"] for e in nb.entries}
    added = 0
    for t in FACTS:
        if t in seen:
            continue
        nb.add(t, type="fact", source="user_confirmed", confidence=0.85,
               importance=0.6)
        seen.add(t)
        added += 1
    print("backup", bak, "added", added, "total", len(nb.entries))


if __name__ == "__main__":
    main()
