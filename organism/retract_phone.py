# -*- coding: utf-8 -*-
"""撤回"华为 P70"事实：主人不确认曾告知，按无确认处理。"""
import json
import os
import shutil
import time

SRC = "evidence/p3/cmw_native/notebook.json"


def main():
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bak = "evidence/p3/backup/notebook-before-retract-phone-%s.json" % stamp
    os.makedirs(os.path.dirname(bak), exist_ok=True)
    shutil.copyfile(SRC, bak)
    d = json.load(open(SRC, encoding="utf-8"))
    n = 0
    for e in d["entries"]:
        if "P70" in e.get("text", "") or "p70" in e.get("text", ""):
            e["status"] = "deleted"
            e["retracted_reason"] = "主人不确认曾告知手机型号；仅凭一句“我p70都成啥了”不足以认定"
            n += 1
    json.dump(d, open(SRC, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("backup", bak, "retracted", n)


if __name__ == "__main__":
    main()
