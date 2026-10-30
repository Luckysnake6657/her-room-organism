# -*- coding: utf-8 -*-
"""完整一条：陌生 → 第一周 → 缺席回来 → "我不记得"。

跑法：python -m organism.demo_meet [--real]
"""
import argparse
import json
import os

from . import notebook, persona
from .chat import Session


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", action="store_true")
    ap.add_argument("--path", default="evidence/p3/demo_meet.json")
    args = ap.parse_args(argv)
    if os.path.exists(args.path):
        os.remove(args.path)

    nb = notebook.Notebook()
    lines = []

    def show(who, text):
        lines.append("%s：%s" % (who, text))
        print(lines[-1])

    # 1) 第一次见面
    s = Session(args.path, dry=not args.real, persona=persona.PERSONA_V1,
                mode="stranger", notebook=nb)
    for q in ("你好", "你是谁啊"):
        show("你", q)
        show("她", s.say(q)["text"])
    lines.append("")

    # 2) 第一周：她开始记
    nb.add("你下周三要去医院复查")
    nb.add("你怕黑")
    nb.add("你养了一只猫叫团子")
    s.mode = "acquaintance"
    show("你", "我下周三要去复查，有点紧张")
    show("她", s.say("我下周三要去复查，有点紧张")["text"])
    show("你", "我复查是什么时候来着？")
    show("她", s.say("我复查是什么时候来着？")["text"])
    lines.append("")

    # 3) 缺席一周
    s._save()
    st = json.load(open(args.path, encoding="utf-8"))
    st["saved_at"] -= 7 * 86400
    with open(args.path, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False)
    s2 = Session(args.path, dry=not args.real, persona=persona.PERSONA_V1,
                 mode="acquaintance", notebook=nb)
    show("你", "这段时间怎么样")
    show("她", s2.say("这段时间")["text"])
    lines.append("")

    # 4) 第一次"我不记得"
    show("你", "你能叫我亲爱的吗")
    show("她", s2.say("你能叫我亲爱的吗")["text"])
    show("你", "你还记得我说过我要辞职吧？")
    show("她", s2.say("你还记得我说过我要辞职吧？")["text"])

    out = "evidence/p3/demo_meet.txt"
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
