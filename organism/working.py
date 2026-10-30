# -*- coding: utf-8 -*-
"""工作记忆：最近 7±2 轮，原文，不摘要。

人的工作记忆（Baddeley）容量就这么大，而且会掉；掉了就是掉了，不压缩成摘要。
这里只做一件事：把最近几轮原样带给嘴，让它接得住指代和追问。
"""
MAXLEN = 7
CLIP = 60


def add(turns: list, role: str, text: str, t: int = None, maxlen: int = MAXLEN):
    turns.append(dict(role=role, text=(text or "")[:CLIP], t=t))
    del turns[:-maxlen]
    return turns


def prompt_lines(turns: list, maxlen: int = MAXLEN) -> list:
    """给简报的几行；只放最近的，不解释、不总结。"""
    out = []
    for x in turns[-maxlen:]:
        who = "你" if x["role"] == "user" else "她"
        out.append("%s：%s" % (who, x["text"]))
    return out
