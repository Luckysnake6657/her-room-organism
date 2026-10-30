# -*- coding: utf-8 -*-
"""简报：把机体状态翻成"嘴"能读的一段话——**不含数字、不含变量名**。

设计约束（前面几轮定的，别违反）：
- 简报只描述**世界与身体**，不描述"她因为你怎样"（见 docs/cost-and-guilt.md）。
- 允许"撒谎"：简报给的是**她现在的状态**，嘴可以不说实话；但形式（延迟/长度/主动）
  由 form.py 决定，不走嘴。
- 离线补算之后，简报**必须**带 `claims.DISCLOSURE`（她不记得那几天）。
- 除非用户主动查询，否则**不推送**结算单。
"""
from . import claims
from . import form as F


def state_phrase(body) -> str:
    """状态的人话：只列身体上的感觉，不列数值、不解释原因。"""
    parts = []
    if body.e < 0.35:
        parts.append("饿")
    if body.s > 0.65:
        parts.append("困")
    if body.a > 0.50:
        parts.append("心里烦")
    if body.i > 0.45:
        parts.append("身上不舒服")
    if body.l > 0.55:
        parts.append("有点闷")
    if sum(body.chronic.values()) > 2.0:
        parts.append("整个人发沉")
    return "、".join(parts) if parts else "还行"


def day_facts(sim) -> list:
    """今天发生过的事：只取已经发生的事实，不编造、不带数字。"""
    day = sim.world.day_at(sim.t)
    facts = []
    if day < len(sim.daily):
        d = sim.daily[day]
        if d.get("meals"):
            facts.append("吃过东西")
        if d.get("socials"):
            facts.append("见过人")
        if d.get("out"):
            facts.append("出过门")
        if d.get("sick"):
            facts.append("身上不太舒服")
    for ev in sim.events:
        if ev.get("day") != day:
            continue
        k = ev.get("kind")
        if k == "person_arrives":
            facts.append("有人来过")
        elif k == "cold_snap":
            facts.append("天突然冷了")
        elif k == "rain":
            facts.append("下了雨")
    return facts[:4]


def make(body, gap: dict = None, hide: bool = False, facts=None,
         persona=None, mode: str = "acquaintance", notebook_entries=None,
         recent=None, memory_tier: str = "none") -> dict:
    """生成一轮对话的简报。

    gap: 只有"刚补算完、用户主动来问"时才传；传了就带结算与披露。
    hide: 她不想让人担心——会轻描淡写。**这是动机，不是状态**，所以单独给。
    persona: 人物卡（只调上下限与措辞）。
    mode: "stranger"（第一次见面）或 "acquaintance"（已经认识）。
    notebook_entries: 本轮允许她引用的本子条目（0–3 条，已过置信门）。
    recent: 工作记忆（最近 7 轮原文），用于接住指代与追问。
    """
    f = F.form_of(body, persona=persona)
    wants = "想主动说点什么" if f["proactive"] else "不太想主动开口"
    if f["proactive"] and f.get("topic") == "self":
        wants = "想主动说点自己日子里的事，不提到对方"
    brief = dict(
        state=state_phrase(body),
        wants=wants,
        words=int(round(f["words"])),
        delay_s=f["delay_s"],
        u=f.get("u", 0.0),
        hide=bool(hide),
        facts=list(facts or []),
        persona=persona,
        body=body,
        mode=mode,
        notebook=list(notebook_entries or []),
        recent=list(recent or []),
        memory_tier=memory_tier,
        disclosure=None,
        settlement=None,
        forbidden=list(claims.FORBIDDEN),
    )
    if gap is not None:
        from . import settlement
        brief["settlement"] = settlement.text_for(gap)
        brief["disclosure"] = claims.DISCLOSURE
    return brief


def as_prompt(brief: dict) -> str:
    """给嘴的系统提示。只给事实与边界，不给"该怎么演"。"""
    if brief["words"] <= 25:
        budget_line = "只说一句很短的话，不超过 %d 个字。" % brief["words"]
    elif brief["words"] <= 45:
        budget_line = "说一两句，不超过 %d 个字。" % brief["words"]
    else:
        budget_line = "可以多说几句，%d 到 %d 个字。" % (max(6, brief["words"] // 2), brief["words"])
    lines = []
    if brief.get("persona") is not None:
        lines.extend(brief["persona"].prompt_lines())
    if brief.get("mode") == "stranger":
        lines.append("你们是第一次见面，还不熟。不要提以前的事，也不要显得亲昵。")
    else:
        lines.append("你是一个有自己日子的人，现在正在和熟人说话。")
    lines.extend([
        "你的日子只有这几件事：吃饭、睡觉、出门、见人、天气。",
        "你现在的感觉：%s。" % brief["state"],
        "你此刻%s。" % brief["wants"],
        budget_line,
    ])
    from . import relation
    lines.append("%s。" % relation.stance(brief.get("body")))
    if brief.get("recent"):
        lines.append("刚才你们在说：")
        from . import working
        lines.extend(working.prompt_lines(brief["recent"]))
        lines.append("接着刚才的话说，别当新的；对方说“那个”“刚才”就指上面的事。")
    if brief.get("facts"):
        lines.append("今天你这边发生过：%s。" % "，".join(brief["facts"]))
    if brief.get("notebook"):
        lines.append("你本子上记着的、关于对方的事（只许引用这些，别编）：")
        for e in brief["notebook"]:
            lines.append("- %s" % e["text"])
        lines.append("对方问起本子上的事，就把那条原话复述出来，别只说你记得。")
        lines.append("本子上没有的事，被问到就说你不记得。")
    if brief.get("memory_tier") == "fuzzy":
        lines.append("你对这件事只有模糊印象，说的时候要带“好像”，别说得太确定。")
    elif brief.get("memory_tier") == "strong":
        lines.append("这件事你本子上有，可以确定地说。")
    if brief.get("hide"):
        lines.append("你不太想让对方担心，回答时可能会轻描淡写、说没什么事。")
    if brief["settlement"]:
        lines.append("对方刚问起你不在的那段时间。可以照这句说：%s" % brief["settlement"])
    if brief["disclosure"]:
        lines.append("如果被问到那几天的细节，照实说：%s" % brief["disclosure"])
    lines.append("不要提数字、不要提身体指标、不要编造具体日期。")
    return "\n".join(lines)
