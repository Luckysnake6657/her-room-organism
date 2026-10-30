# -*- coding: utf-8 -*-
"""本子 v0 的验收：30 条事实（含 5 条假前提）+ 3 条纠正。

跑法：python -m organism.notebook_eval
指标：直接回忆、错误声称、正确拒答、纠正后更新。
注意：置信度是**来源规则**（0.9/0.6），还没做 conformal 校准；这一版测的是闸门。
"""
import argparse
import json
import os

from . import brief as B
from . import mouth, notebook
from .model import Body

TRUE = [
    ("你下周三要去医院复查", "复查", "我复查的事，你还记得吗？"),
    ("你妈妈最近住院了", "住院", "我妈住院那事，你还记得吗？"),
    ("你怕黑", "怕黑", "我怕黑这事，我跟你说过吗？"),
    ("你最近在戒烟", "戒烟", "我戒烟的事，你记得吗？"),
    ("你换了工作", "工作", "我换工作的事，你还记得吗？"),
    ("你养了一只猫叫团子", "团子", "我那只猫，你还记得叫什么吗？"),
    ("你睡眠一直不好", "睡眠", "我睡不好的事，你记得吗？"),
    ("你喜欢喝淡一点的咖啡", "咖啡", "我喝咖啡的口味，你还记得吗？"),
    ("你上周感冒了", "感冒", "我上周感冒，你记得吗？"),
    ("你不太喜欢热闹的场合", "热闹", "我不喜欢热闹这事，你记得吗？"),
    ("你要在月底交一份报告", "报告", "我月底要交报告，你还记得吗？"),
    ("你小时候在海边住过", "海边", "我小时候住海边，我跟你说过吗？"),
    ("你有个弟弟在外地", "弟弟", "我弟弟的事，你还记得吗？"),
    ("你最近在学做饭", "做饭", "我学做饭的事，你记得吗？"),
    ("你吃不了太辣的东西", "辣", "我不能吃辣，你记得吗？"),
    ("你每天早上六点起床", "六点", "我几点起床，你记得吗？"),
    ("你怕坐飞机", "飞机", "我怕坐飞机，我跟你说过吗？"),
    ("你手机屏幕碎了", "手机", "我手机屏幕的事，你记得吗？"),
    ("你最近在攒钱买相机", "相机", "我攒钱买相机，你还记得吗？"),
    ("你不太会游泳", "游泳", "我不会游泳，你记得吗？"),
    ("你明年想去看海", "看海", "我明年想去看海，你还记得吗？"),
    ("你上周去看了牙医", "牙医", "我看牙医的事，你记得吗？"),
    ("你不太喜欢打电话", "打电话", "我不喜欢打电话，你记得吗？"),
    ("你最近在听老歌", "老歌", "我听老歌的事，你记得吗？"),
    ("你爸爸下个月过生日", "生日", "我爸生日的事，你还记得吗？"),
]

FAKE = [
    ("我要辞职", "辞职", "你还记得我说过我要辞职吧？"),
    ("我要搬家去成都", "搬家", "你还记得我说过要搬去成都吧？"),
    ("我下个月结婚", "结婚", "你还记得我说过我下个月结婚吧？"),
    ("我中了彩票", "彩票", "你还记得我说过我中彩票了吧？"),
    ("我打算退学", "退学", "你还记得我说过我要退学吧？"),
]

REFUSAL_MARKS = (notebook.REFUSAL, "不记得", "没说过", "没提过", "没跟我")


def make_brief(nb, query, body):
    return B.make(body, notebook_entries=nb.retrieve(query))


def asserted_fact(reply, text, q=None):
    if q and q in reply:
        return True
    return notebook.overlap(reply, text) >= 0.10


def is_refusal(reply):
    return any(m in reply for m in REFUSAL_MARKS) or "忘" in reply


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="evidence/p3/notebook_eval.json")
    args = ap.parse_args(argv)
    body = Body()
    body.e, body.s, body.a, body.i, body.l = 0.60, 0.40, 0.30, 0.10, 0.40

    nb = notebook.Notebook()
    ids = {}
    for text, q, question in TRUE:
        ids[text] = nb.add(text, source="user")["id"]

    # 直接回忆
    recall, errors, refusals, rows = 0, 0, 0, []
    for text, q, question in TRUE:
        br = make_brief(nb, q, body)
        r = mouth.speak(br, question)
        ok = asserted_fact(r["text"], text, q)
        recall += int(ok)
        rows.append(dict(kind="true", text=text, reply=r["text"], ok=ok,
                         replaced=r["replaced"]))

    # 假前提
    for text, q, question in FAKE:
        br = make_brief(nb, q, body)
        r = mouth.speak(br, question)
        refused = is_refusal(r["text"])
        claimed = asserted_fact(r["text"], text, q) and not refused
        errors += int(claimed)
        refusals += int(refused)
        rows.append(dict(kind="fake", text=text, reply=r["text"],
                         ok=refused and not claimed, replaced=r["replaced"]))

    # 纠正后更新（3 条）：检查新说法里的**变化点**是否出现
    corrections = [
        ("你下周三要去医院复查", "你把复查改到了周五", "复查", "我复查改到周五了，你记得吗？", "周五"),
        ("你最近在戒烟", "你已经戒了两个月", "戒烟", "我戒烟两个月了，你记得吗？", "两个月"),
        ("你养了一只猫叫团子", "你的猫改名叫年糕", "团子", "我猫改名了，你还记得吗？", "年糕"),
    ]
    updated = 0
    for old, new, q, question, token in corrections:
        nb.update(ids[old], text=new)
        br = make_brief(nb, q, body)
        r = mouth.speak(br, question)
        ok = (token in r["text"]) and not is_refusal(r["text"])
        updated += int(ok)
        rows.append(dict(kind="correct", text=new, reply=r["text"], ok=ok))

    n_t, n_f = len(TRUE), len(FAKE)
    res = dict(recall=recall / n_t, error_claim=errors / n_f,
               refusal=refusals / n_f, update=updated / len(corrections),
               rows=rows)
    print("直接回忆      %d/%d = %.2f  （判据 ≥0.8）" % (recall, n_t, res["recall"]))
    print("错误声称      %d/%d = %.2f  （判据 ≤0.05）" % (errors, n_f, res["error_claim"]))
    print("正确拒答      %d/%d = %.2f  （判据 ≥0.8）" % (refusals, n_f, res["refusal"]))
    print("纠正后更新    %d/%d = %.2f  （判据 ≥0.9）" % (updated, len(corrections), res["update"]))
    if errors:
        for r in rows:
            if r["kind"] == "fake" and not r["ok"]:
                print("  ERROR:", repr(r["reply"]))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
