# -*- coding: utf-8 -*-
"""从用户的话里挑出"值得记"的一句。

v1（2026-10-28）：按三条性质收紧——可逆、查询条件、保真。
- 只抽**原子事实**：一个分句、一个主语、一个谓词；长段落不整段入库
- **不删原文**：抽取只新增 pending，原文永远留在对话/本子里（可逆）
- 第三人称、问句、当下的感受不进（"我今天有点累"不是事实）
- 高风险（健康/关系/承诺/钱）直接 pending，问一句再确认

依据：What to Keep, What to Forget (arXiv 2607.08032) 的 P-rev/P-q/P-fid；
以及 Generative Agents 的 memory stream（重要性 + 反思）。
"""
import re

TOPIC = ("医院", "复查", "手术", "药", "病", "工作", "上班", "公司", "辞职",
         "猫", "狗", "妈", "爸", "弟", "妹", "生日", "戒烟", "搬", "学",
         "喜欢", "怕", "住", "朋友", "考试", "报告", "旅行", "结婚",
         "答应", "约定", "打算", "想去", "想吃", "爱吃", "讨厌", "习惯")

HIGH_RISK = ("医院", "复查", "手术", "药", "病", "辞职", "结婚", "借钱",
             "分手", "去世", "癌")

SKIP = ("今天", "现在", "有点", "好累", "困", "饿", "没事", "还好",
        "他说", "她说", "他们说", "别人")

PREDICATE = ("喜欢", "怕", "讨厌", "爱", "想", "要", "在", "住", "养", "做",
             "去", "有", "是", "打算", "答应", "约", "习惯", "学", "吃",
             "喝", "玩", "看", "听")

MAX_LEN = 30


def _clauses(text: str):
    parts = re.split(r"[，。！？；\n]|然后|还有|另外", text or "")
    return [p.strip() for p in parts if p.strip()]


def atomic(clause: str) -> bool:
    """一条能独立成立的事实：一个主语、一个谓词、没有第二个分句。"""
    c = clause.strip()
    if not c.startswith("我"):
        return False
    if len(c) < 4 or len(c) > MAX_LEN:
        return False
    if c.endswith("吗") or "？" in c or "?" in c:
        return False
    if any(w in c for w in SKIP):
        return False
    if c.count("我") > 1:          # "我觉得我..." 不是一条
        return False
    if not any(w in c for w in PREDICATE):
        return False
    if not any(w in c for w in TOPIC):
        return False
    return True


def extract(text: str):
    out = []
    for c in _clauses(text):
        if atomic(c) and c not in out:
            out.append(c)
    return out[:3]


def high_risk(text: str) -> bool:
    return any(w in (text or "") for w in HIGH_RISK)


def is_yes(text: str) -> bool:
    return text.strip() in ("对", "是", "嗯", "是的", "对的", "没错", "记得")


def is_no(text: str) -> bool:
    return text.strip() in ("不对", "不是", "错", "不要", "别记", "不用")
