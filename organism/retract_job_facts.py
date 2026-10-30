# -*- coding: utf-8 -*-
"""撤回误判的工作类事实（标记 deleted，保留审计）。"""
import os
import shutil
import time

from . import notebook

BAD_KEYS = ["薪资", "toB", "硬扛", "保底"]


def main():
    src = "evidence/p3/cmw_native/notebook.json"
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bak = "evidence/p3/backup/notebook-before-retract-%s.json" % stamp
    os.makedirs(os.path.dirname(bak), exist_ok=True)
    shutil.copyfile(src, bak)
    nb = notebook.Notebook(src)
    n = 0
    for e in nb.entries:
        if e.get("source") != "user_confirmed":
            continue
        if any(k in e["text"] for k in BAD_KEYS):
            e["status"] = "deleted"
            e["retracted_reason"] = "用户是学生，工作类事实为误判"
            n += 1
    nb.save()
    print("backup", bak, "retracted", n, "total", len(nb.entries))


if __name__ == "__main__":
    main()
