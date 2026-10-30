# -*- coding: utf-8 -*-
"""按管理员要求撤回两条事实：小5金哲、自称来就通关。"""
import json
import os
import shutil
import time

SRC = "evidence/p3/cmw_native/notebook.json"
KEYS = ("小5金哲", "通关")


def main():
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bak = "evidence/p3/backup/notebook-before-retract-2-%s.json" % stamp
    os.makedirs(os.path.dirname(bak), exist_ok=True)
    shutil.copyfile(SRC, bak)
    d = json.load(open(SRC, encoding="utf-8"))
    n = 0
    for e in d["entries"]:
        if e.get("source") != "user_confirmed" or e.get("status") == "deleted":
            continue
        if any(k in e.get("text", "") for k in KEYS):
            e["status"] = "deleted"
            e["retracted_reason"] = "管理员确认删除（推断不可靠）"
            n += 1
            print("deleted:", e["text"])
    json.dump(d, open(SRC, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    live = sum(1 for e in d["entries"] if e.get("source") == "user_confirmed" and e.get("status") != "deleted")
    print("backup", bak, "deleted", n, "live_facts", live)


if __name__ == "__main__":
    main()
