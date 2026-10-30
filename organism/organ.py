# -*- coding: utf-8 -*-
"""器官接口：把意图说成话。换模型只换这一层。

- 只看 intent + brief，不读人格卡、不决定说什么
- 在线走 API，断网走本地 1.5B（mouth 里已经路由）
- 拒答/回忆这类 move 不生成，直接给固定文本或本子原话
"""
import copy

from . import intent as I
from . import mouth, notebook


def render(intent: dict, brief: dict, user_text: str = "", backend: str = "auto") -> dict:
    move = intent.get("move", "answer")

    if move == "refuse":
        return dict(text=notebook.REFUSAL, delay_s=brief.get("delay_s", 0.0),
                    proactive=False, used_api=False, offline=False, replaced=True,
                    hits=[("intent", "refuse")])

    if move == "recall" and brief.get("notebook"):
        e = brief["notebook"][0]
        if brief.get("memory_tier") == "fuzzy":
            return dict(text="我好像记得，" + e["text"], delay_s=brief.get("delay_s", 0.0),
                        proactive=False, used_api=False, offline=False, replaced=True,
                        hits=[("intent", "fuzzy")])
        return dict(text=notebook.quote(e), delay_s=brief.get("delay_s", 0.0),
                    proactive=False, used_api=False, offline=False, replaced=True,
                    hits=[("intent", "recall")])

    adj = I.form_adjust(intent, copy.deepcopy(brief))
    if move == "initiate":
        return mouth.initiate(adj)
    return mouth.speak(adj, user_text)
