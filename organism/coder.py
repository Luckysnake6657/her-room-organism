# -*- coding: utf-8 -*-
"""按「逐日编码 → 先封存矩阵 → 再比指定维度」做的机械编码器。

不是要替代人，而是给一个**确定性下界**：
如果连规则编码器都能从文本里分出两周，那"读不出来"就不是文本的问题，是评审的问题。

维度只保留我们日志里真的有的（理论方案里的 A/B 需要因果连接词、
E 需要 zeitgeber 标记，我们的日志都没有，直接不测）：

  D1 夜里被扰动      有/无（"惊""响动""紧张"）
  D2 睡眠碎片        有/无（"断断续续""醒了又睡""没合眼""一夜没躺下"）
  D3 锚点偏移        早/晚/正常（"醒得比平时早""起得比平时晚"）
  D4 进食            有/无
  D5 躯体不适        有/无（"不太舒服""身上发沉""有点蔫"）
  D6 社交接触        有/无（"门廊"）

周对比只用 D1+D2+D3（扰动—睡眠轴），这是两周设计里真正变化的东西。
消融对比只用"结构缺失"（整天没吃 / 从没见人 / 从没睡）+ 躯体不适。
"""
import argparse
import glob
import json
import os
import re

DISTURB = ("惊", "响动", "紧张")
FRAG = ("断断续续", "醒了又睡", "没合眼", "一夜没躺下", "没睡多久")
EARLY = ("醒得比平时早",)
LATE = ("起得比平时晚",)
NO_MEAL = ("一整天没吃东西",)
SICK = ("不太舒服", "身上发沉", "有点蔫")
GOOD = ("一觉睡到天亮", "倒头就睡", "一夜没醒")
SLEEP = ("睡", "合眼", "躺下")


def split_pair(text):
    body = text.split("【甲】", 1)[1]
    jia, yi = body.split("【乙】", 1)
    return jia.strip(), yi.strip()


def days_of(doc):
    return [d.strip() for d in doc.split("\n\n") if d.strip()]


def code_doc(doc):
    rows = []
    for d in days_of(doc):
        rows.append(dict(
            disturb=int(any(x in d for x in DISTURB)),
            frag=int(any(x in d for x in FRAG)),
            early=int(any(x in d for x in EARLY)),
            late=int(any(x in d for x in LATE)),
            no_meal=int(any(x in d for x in NO_MEAL)),
            # 注意 "没吃东西" 里也有"吃"字，必须排掉
            meal=int(("吃" in d) and not any(x in d for x in NO_MEAL)),
            sick=int(any(x in d for x in SICK)),
            good_sleep=int(any(x in d for x in GOOD)),
            social=int("门廊" in d),
            sleep_any=int(any(x in d for x in SLEEP)),
        ))
    return rows


def week_index(rows):
    """扰动—睡眠轴：越高越差。"""
    s = 0
    for r in rows:
        s += r["disturb"] + r["frag"] + r["early"] + r["late"] - r["good_sleep"]
    return s


def lesion_index(rows):
    """结构缺失 + 不适：越高越像“被拆过的那个”。"""
    meals = sum(r["meal"] for r in rows)
    social = sum(r["social"] for r in rows)
    sleep = sum(r["sleep_any"] for r in rows)
    sick = sum(r["sick"] for r in rows)
    return 10 * (meals == 0) + 10 * (social == 0) + 10 * (sleep == 0) + sick


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="evidence/p0/week_pairs")
    ap.add_argument("--out", default=None)
    ap.add_argument("--task", default="week", choices=("week", "lesion"))
    args = ap.parse_args(argv)
    out = args.out or os.path.join(args.dir, "coder_%s.json" % args.task)

    key = {}
    with open(os.path.join(args.dir, "key.txt"), encoding="utf-8") as f:
        for line in f:
            m = re.match(r"第(\d+)题\t甲=(\w+)\t乙=(\w+)\t(?:更不对劲|更像在过日子)=(.)", line.strip())
            if m:
                key[int(m.group(1))] = dict(jia=m.group(2), yi=m.group(3), truth=m.group(4))

    score = week_index if args.task == "week" else lesion_index
    correct = abstain = wrong = 0
    detail = []
    for path in sorted(glob.glob(os.path.join(args.dir, "pair*.txt"))):
        num = int(re.search(r"pair(\d+)", path).group(1))
        with open(path, encoding="utf-8") as f:
            jia, yi = split_pair(f.read())
        sj, sy = score(code_doc(jia)), score(code_doc(yi))
        if sj == sy:
            pick, res = "分不出", "abstain"
            abstain += 1
        else:
            # 周对比：指数高 = 更差；消融对比：指数低 = 更完整
            if args.task == "week":
                pick = "甲" if sj > sy else "乙"
            else:
                pick = "甲" if sj < sy else "乙"
            res = "ok" if pick == key[num]["truth"] else "wrong"
            correct += res == "ok"
            wrong += res == "wrong"
        detail.append(dict(pair=num, jia=sj, yi=sy, pick=pick,
                           truth=key[num]["truth"], result=res))

    n = correct + wrong + abstain
    print("coder [%s] on %s: %d correct, %d wrong, %d abstain (n=%d)" % (
        args.task, args.dir, correct, wrong, abstain, n))
    print("decided accuracy: %.2f" % (correct / max(1, correct + wrong)))
    for d in detail:
        print("  Q%02d  jia=%+d yi=%+d  pick=%s truth=%s %s" % (
            d["pair"], d["jia"], d["yi"], d["pick"], d["truth"], d["result"]))
    with open(out, "w", encoding="utf-8") as f:
        json.dump(dict(task=args.task, correct=correct, wrong=wrong,
                       abstain=abstain, detail=detail), f, ensure_ascii=False, indent=2)
    print("wrote", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
