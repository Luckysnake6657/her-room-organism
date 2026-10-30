# -*- coding: utf-8 -*-
"""意图层：她此刻想干什么。**与用哪个器官无关。**

输入：身体（状态/regard/孤独）、记忆档位、是不是在问记忆
输出：move（回答/追问/岔开/沉默/主动/拒答/回忆）+ urgency

器官只负责把 move 说成话；换模型不影响 move。
"""
from . import params as P

# 混合主动（Horvitz 1999）：只有明确的办事请求才进 task；其余过日子。
TASK_MARKERS = ("帮我", "看一下", "看看这个", "查一下", "弄一下", "写个", "改一下",
                "一起弄", "怎么弄", "报错", "代码", "文件", "算一下", "翻译",
                "弄好", "好了告诉我", "再试", "试试", "读不到", "检查", "报给")


def _clip(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def decide_mode(body, text: str) -> str:
    """life / task / defer。默认 life；状态差时请求也 defer。"""
    t = str(text or "")
    wants_task = any(m in t for m in TASK_MARKERS)
    if not wants_task:
        return "life"
    # 介入成本（Horvitz）：太累/太烦就不接，宁可晚点
    if float(body.a) > 0.70 or float(body.e) < 0.25 or float(body.D()) > 1.6:
        return "defer"
    return "task"


def decide(body, memory_tier: str = "none", asked_memory: bool = False,
           proactive_ok: bool = False) -> dict:
    a = float(body.a)
    l = float(body.l)
    r = float(body.regard)
    D = float(body.D())

    if asked_memory and memory_tier == "none":
        move = "refuse"
    elif asked_memory and memory_tier in ("strong", "fuzzy"):
        move = "recall"
    elif a > 0.60 or D > 1.8:
        move = "brief"          # 烦/状态差：短答，不展开
    elif r < 0.35:
        move = "guarded"        # 对他有保留：收着说
    elif l > 0.60 and proactive_ok:
        move = "initiate"       # 孤独：可能先开口
    else:
        move = "answer"

    urgency = _clip((a + D / 3.0) / 2.0)
    # A1 的闸门：状态差/有保留时不主动发问（问句是索取，状态差时不该索取）
    no_question = move in ("brief", "guarded")
    return dict(move=move, urgency=round(urgency, 3),
                target="user", memory_tier=memory_tier, no_question=no_question)


# 每种 move 对形式的影响（只动字数/是否主动，不动人）
WORDS_FACTOR = dict(answer=1.0, brief=0.55, guarded=0.65, recall=1.0,
                    refuse=1.0, initiate=1.0)


def form_adjust(intent: dict, brief: dict) -> dict:
    """返回一份改过的 brief（不改原对象），器官照这个说。"""
    b = dict(brief)
    f = WORDS_FACTOR.get(intent["move"], 1.0)
    b["words"] = max(P.FORM_WORDS_MIN, int(round(b["words"] * f)))
    b["intent"] = intent
    return b
