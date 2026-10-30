# -*- coding: utf-8 -*-
"""她是她：一个命令就能用的入口。

把人物卡、本子、会话、断网提示、导出/删除接在一起。

    python -m organism.app                 # 真嘴（API，断网退本地）
    python -m organism.app --dry           # 不加载模型，测试用
    python -m organism.app --home evidence/p3/app

命令：
    /notebook        看本子
    /forget <id>     删一条
    /export <文件>   导出（不含 key）
    /delete          删掉全部（要再输 yes）
    /what            数据告知
    /exit
"""
import argparse
import os

from . import consolidate, forget, memorize, notebook, persona, privacy
from .chat import Session
from .offline import Notice


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", default="evidence/p3/app")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args(argv)

    os.makedirs(args.home, exist_ok=True)
    sess_path = os.path.join(args.home, "session.json")
    nb_path = os.path.join(args.home, "notebook.json")
    first_time = not os.path.exists(sess_path)

    nb = notebook.Notebook(nb_path)
    forget.sweep(nb)                      # 先结算遗忘
    suggested = 0
    for c in consolidate.candidates(nb):  # 再把反复出现的事挑出来（逐字，不编）
        if consolidate.apply(nb, c):
            suggested += 1
    s = Session(sess_path, dry=args.dry, persona=persona.PERSONA_V1,
                mode="stranger" if first_time else "acquaintance",
                notebook=nb)
    notice = Notice()
    pending = None

    print("（/notebook 看本子，/what 数据告知，/exit 退出）")
    if suggested:
        print("（理了理本子，有 %d 条等你确认：/notebook 看，/confirm id 确认）" % suggested)
    g = s.greeting()
    if g:
        print("她：%s" % g["text"])

    while True:
        try:
            line = input("你：").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue

        if line == "/exit":
            break
        if line == "/what":
            print(privacy.disclosure())
            continue
        if line == "/notebook":
            for e in nb.live():
                print("  [%d] %s  (%s, %.2f)" % (e["id"], e["text"], e["status"], e["confidence"]))
            continue
        if line.startswith("/forget "):
            try:
                nb.delete(int(line.split()[1]))
                print("（删了）")
            except Exception:
                print("（没有这条）")
            continue
        if line.startswith("/confirm "):
            try:
                nb.confirm(int(line.split()[1]))
                print("（记下了）")
            except Exception:
                print("（没有这条）")
            continue
        if line.startswith("/export"):
            out = line.split(maxsplit=1)[1] if " " in line else "export.json"
            privacy.export(sess_path, nb_path, out)
            print("（导出到 %s，不含 key）" % out)
            continue
        if line == "/delete":
            print("删掉全部？再输 yes 确认")
            if input("> ").strip() == "yes":
                privacy.delete(sess_path, nb_path)
                print("（删了）")
                break
            continue

        # 待确认的记忆
        if pending is not None:
            if memorize.is_yes(line):
                nb.confirm(pending)
                print("（记下了）")
                pending = None
                continue
            if memorize.is_no(line):
                nb.delete(pending)
                print("（那就不记）")
                pending = None
                continue
            pending = None

        r = s.say(line)
        print("她：%s" % r["text"])
        if r.get("offline"):
            msg = notice.fallback()
            if msg:
                print("（%s）" % msg)

        for c in memorize.extract(line):
            if memorize.high_risk(c):
                e = nb.propose(c, source=line)
                pending = e["id"]
                print("（记一句：%s —— 对吗？对/不对）" % c)
            else:
                nb.add(c, source=line)
                print("（记下了：%s）" % c)

        if first_time and s.mode == "stranger":
            s.mode = "acquaintance"
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
