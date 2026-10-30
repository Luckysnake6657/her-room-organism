# -*- coding: utf-8 -*-
"""检索打分：相关 0.5 + 新近 0.3 + 重要 0.2（Generative Agents 的配方）。

分数决定三件事：
- 进不进简报（<0.05 不进）
- 元记忆措辞（≥0.7 确定 / 0.4–0.7 模糊 / <0.4 没记）
- 访问刷新遗忘强度（由 forget 模块处理）
"""
import datetime as dt

from . import notebook

W_REL, W_REC, W_IMP = 0.5, 0.3, 0.2
TIER_STRONG = 0.70
TIER_FUZZY = 0.40


def _age_days(entry, now):
    try:
        t = dt.datetime.strptime(entry["created_at"], "%Y-%m-%dT%H:%M:%S")
    except Exception:
        return 30.0
    return max(0.0, (now - t).total_seconds() / 86400.0)


def score(entry, query, now=None, importance=None) -> float:
    now = now or dt.datetime.now()
    text = entry["text"] + " " + entry.get("keywords", "")
    rel = notebook.overlap(query, text)
    if rel <= 0:
        return 0.0
    rec = 0.5 ** (_age_days(entry, now) / 14.0)
    imp = float(entry.get("importance", 0.5) if importance is None else importance)
    return W_REL * rel + W_REC * rec + W_IMP * imp


def tier(score_value: float) -> str:
    if score_value >= TIER_STRONG:
        return "strong"
    if score_value >= TIER_FUZZY:
        return "fuzzy"
    return "none"


FILLER = ("你还记得", "你记得", "还记得", "记得", "帮我查一下", "查一下",
          "吗", "呢", "呀", "吧", "请问", "我想问")


def _content(q: str) -> str:
    s = str(q or "").strip()
    for f in FILLER:
        s = s.replace(f, "")
    return s or str(q or "")


STOP = set("我你他的了吗呢是什么哪多少几怎么为什么时候请问这那有个就都也还")


def _clean_for_match(q: str) -> str:
    s = "".join(ch for ch in str(q or "") if ch not in STOP)
    return s or str(q or "")


def _bigrams(s: str):
    s = "".join(ch for ch in str(s or "") if ch.strip())
    return [s[i:i + 2] for i in range(max(0, len(s) - 1))] or [s]


def _bigram_rel(q: str, text: str) -> float:
    qs = set(_bigrams(q))
    ts = set(_bigrams(text))
    return len(qs & ts) / (len(qs) or 1)


def retrieve(nb, query, now=None, k: int = 3, min_score: float = 0.05,
             min_rel: float = 0.5):
    now = now or dt.datetime.now()
    query = _content(query)
    scored = []
    for e in nb.live():
        conf = e.get("calibrated")
        if conf is None:
            conf = e["confidence"]
        if conf < notebook.THETA or e["status"] == "pending":
            continue
        text = e["text"] + " " + e.get("keywords", "")
        rel = max(notebook.overlap(query, text),
                  _bigram_rel(query, text),
                  _bigram_rel(_clean_for_match(query), text))
        if rel < min_rel:
            continue
        s = score(e, query, now)
        if s >= min_score:
            scored.append((s, e))
    scored.sort(key=lambda x: -x[0])
    return [(round(s, 3), e) for s, e in scored[:k]]
