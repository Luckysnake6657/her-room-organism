# -*- coding: utf-8 -*-
"""披露策略：说不说、说多少。AADE 第 3 层。

不生成文字，只给 mode：none / brief / elaborate / seek_response
"""
import re

ASK = re.compile(r"怎么|咋样|感觉|还好吗|难受|累不累|困不困|开心|不高兴|怎么了|在吗")
FEEL = re.compile(r"感觉|难受|累|困|烦|闷|开心|不高兴|怎么了|咋样")


def intensity(affect):
    v = float(affect.get("valence", 0.5))
    a = float(affect.get("arousal", 0.2))
    return round(min(1.0, abs(v - 0.5) * 1.2 + a * 0.4), 3)


def decide(affect, text="", relation="owner_private", asked_feeling=None,
           disclosed_today=False):
    """relation: owner_private | group | other"""
    i = intensity(affect)
    t = str(text or "")
    if asked_feeling is None:
        asked_feeling = bool(ASK.search(t)) and bool(FEEL.search(t))
    lonely = float(affect.get("lonely", 0.0)) if "lonely" in affect else 0.0

    if disclosed_today and relation != "owner_private":
        return dict(mode="none", reason="今天说过，不重复")
    if relation == "group":
        if asked_feeling and i >= 0.6:
            return dict(mode="brief", reason="群里被问且强度高")
        return dict(mode="none", reason="群里不主动披露")
    if relation == "other":
        if asked_feeling and i >= 0.5:
            return dict(mode="brief", reason="被问，简短")
        return dict(mode="none", reason="不熟，不说")
    # owner_private
    if asked_feeling:
        if i >= 0.5:
            return dict(mode="elaborate", reason="他问且强度高")
        return dict(mode="brief", reason="他问，简短")
    if lonely >= 0.6 and i >= 0.5:
        return dict(mode="seek_response", reason="孤独且强度高，主动求回应")
    if i >= 0.75:
        return dict(mode="brief", reason="强度很高，带一句")
    return dict(mode="none", reason="没问、强度不够，不说")
