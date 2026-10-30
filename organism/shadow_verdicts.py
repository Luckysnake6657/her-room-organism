# -*- coding: utf-8 -*-
"""89 条影子事实的人工分类：merge / review / skip。"""
import json

MERGE = {
    49: "设备：华为 P70",
    55: "经历：搜过 AIGC/LLM/Agent",
    56: "经历：SD 刚出时用过",
    62: "经历：发过小说文件",
    67: "社交：想拉小5金哲一起",
    70: "选择：考研还是找工作",
    73: "游戏：S25 零场",
    74: "游戏：历史 295 场",
    75: "游戏：S24 最高 1790",
    76: "游戏：Rating 1.14",
    77: "游戏：KD 1.23",
    78: "游戏：胜率 51%",
    88: "表达：句子短、多语气词",
}
REVIEW = {
    39: "是否'不需要向他汇报'，语义不清",
    43: "偏好：不需要对方什么都对他说",
    44: "偏好：真有事再告诉他",
    48: "计划：她难受就租云服务器",
    50: "帮他打过什么，指代不明",
    51: "游戏：自称来就通关",
    53: "习惯：会引用时间跨度大的消息",
    54: "偏好：有结果后被告知",
    58: "对群聊限制的看法，像观点不像事实",
    63: "薪资：你不认这条",
    64: "工作：你不认这条",
    65: "经历：你不认这条",
    82: "保底：你不认这条",
    80: "训练：提到过训练量",
    81: "引语像玩笑，需确认",
}


def main():
    alln = list(range(1, 90))
    verdicts = {}
    for n in alln:
        if n in MERGE:
            verdicts[n] = dict(verdict="merge", reason=MERGE[n])
        elif n in REVIEW:
            verdicts[n] = dict(verdict="review", reason=REVIEW[n])
        else:
            verdicts[n] = dict(verdict="skip", reason="指令/工程/瞬时/群聊/小说内容")
    counts = {v: sum(1 for x in verdicts.values() if x["verdict"] == v)
              for v in ("merge", "review", "skip")}
    json.dump(dict(counts=counts, verdicts=verdicts),
              open("evidence/p3/shadow_verdicts.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    with open("evidence/p3/shadow_merge_reviewed.md", "w", encoding="utf-8") as f:
        f.write("# 89 条影子事实：审阅结论\n\n")
        f.write("| 结论 | 条数 |\n|---|---|\n")
        for k, v in counts.items():
            f.write("| %s | %d |\n" % (k, v))
        f.write("\n## 建议并入（%d 条）\n\n" % counts["merge"])
        for n, r in sorted(MERGE.items()):
            f.write("- #%d %s（%s）\n" % (n, r, "确认" if n in MERGE else ""))
        f.write("\n## 需再确认（%d 条）\n\n" % counts["review"])
        for n, r in sorted(REVIEW.items()):
            f.write("- #%d %s\n" % (n, r))
        f.write("\n## 其余 %d 条：不并入\n\n" % counts["skip"])
        f.write("含指令、工程日志、瞬时事件、群聊梗、以及 **小说/角色扮演内容（#83–86）**。\n")
    print(json.dumps(counts, ensure_ascii=False))


if __name__ == "__main__":
    main()
