# -*- coding: utf-8 -*-
"""把一个现成人物（卡 + 记忆）接进原生架构。

人格：原文卡原样，不改写；只从卡里读，不从卡里编。
器官：沿用 mouth 的后处理（禁语/事实/本子/边界），但提示词换成她的卡。
"""
from . import mouth


class LegacyPersona:
    """给 form/brief 用的人物壳：卡是原文，形式参数来自她的历史。"""

    def __init__(self, card: str, name: str = "她", words_base: float = 13.0,
                 words_mul: float = 1.0, delay_mul: float = 1.0):
        self.id = "legacy"
        self.version = "imported-1"
        self.name = name
        self.card = card
        self.traits = []
        self.bio = []
        self.world_terms = ()
        self.words_base = float(words_base)
        self.words_mul = float(words_mul)
        self.delay_mul = float(delay_mul)
        self.allow_proactive = True

    def prompt_lines(self):
        return [self.card.strip()]

    def world_bans(self):
        return []

    def validate(self):
        return []


def prompt(brief: dict, user_text: str = "") -> str:
    """她的卡 + 此刻状态 + 记忆 + 最近 + 她自己的话当样例。"""
    from . import corpus
    w = brief["words"]
    if w <= 25:
        budget = "只说一句，不超过 %d 个字。" % w
    elif w <= 45:
        budget = "说一两句，不超过 %d 个字。" % w
    else:
        budget = "说几句，%d 到 %d 个字。" % (max(6, w // 2), w)

    lines = [brief["persona"].card.strip(), "",
             "【现在】%s。" % brief["state"]]
    if brief.get("mood"):
        lines.append("【你最近的底色】%s。" % brief["mood"])
    if brief.get("bdi"):
        from . import bdi as _bdi
        for line in _bdi.lines(brief["bdi"]):
            lines.append("【他现在】%s。" % line)
        lines.append("回话要接住他具体在忙的事、或他此刻的情绪；别给泛泛的建议。")
    if brief.get("impressions"):
        lines.append("【你印象里的人（不是事实，只影响你怎么说话）】")
        for s in brief["impressions"][:5]:
            lines.append("- %s" % s)
    if brief["wants"].startswith("想主动"):
        lines.append("你想主动说一句。")
    if brief.get("mode") == "task":
        lines.append("现在在办事：可以说清楚，必要时分点；该用工具就用。")
    elif brief.get("mode") == "life":
        lines.append("现在在过日子：短一点，别像在办事。")
    lines.append(budget)
    samples = corpus.pick(user_text or brief["state"], 6)
    if samples:
        lines.append("【你以前发消息的样子（只学语气和长度，别照抄）】")
        for s in samples:
            lines.append("- %s" % s)
    if brief.get("recent"):
        from . import working
        lines.append("【刚才】")
        lines.extend(working.prompt_lines(brief["recent"]))
    if brief.get("notebook"):
        lines.append("【你记得的事，只许说这些】")
        for e in brief["notebook"]:
            lines.append("- %s" % e["text"])
        lines.append("本子上没有的，被问到就说你不记得，别编。")
    if brief.get("memory_tier") == "fuzzy":
        lines.append("这件事你只有模糊印象，说的时候带“好像”。")
    lines.append("不要提数字、不要提身体指标、不要编日期。")
    return "\n".join(lines)


def speak(brief: dict, user_text: str, max_tokens: int = 200) -> dict:
    raw, used_api, offline = mouth._raw(prompt(brief, user_text), user_text, max_tokens, 0.85)
    out = mouth._postprocess(raw, brief, user_text, brief["wants"].startswith("想主动"))
    if brief.get("no_question"):
        out["text"] = out["text"].replace("？", "。").replace("?", "。")
    out.update(used_api=used_api, offline=offline)
    return out
