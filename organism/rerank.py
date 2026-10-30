# -*- coding: utf-8 -*-
"""检索重排：LLM 只排序，不负责弃权；说"无"时回退字面 top1。

影子结论（docs/SHADOW-RERANK.md）：同池下重排 41 vs 字面 7，
但弃权 51% 会造成损失，所以加 fallback。
"""
import re

from . import api_client, retrieval

POOL_K = 10
MIN_REL = 0.3

PROMPT = """查询：%s

候选：
%s

挑出最多 3 条能回答查询的候选，按相关度排序；都不行就输出 none。
只输出编号，逗号分隔，例如 3,1；或 none。"""


def _llm_pick(query, texts):
    body = "\n".join("%d. %s" % (i + 1, t[:100]) for i, t in enumerate(texts))
    raw = api_client.chat(PROMPT % (query, body), "", max_tokens=1500, temperature=0.0)
    if "none" in raw.lower():
        return []
    idx = []
    for tok in re.findall(r"\d+", raw):
        i = int(tok) - 1
        if 0 <= i < len(texts) and i not in idx:
            idx.append(i)
    return idx[:3]


def retrieve(nb, query, k: int = 3, use_llm: bool = True, fallback: bool = True):
    cand = retrieval.retrieve(nb, query, k=POOL_K, min_rel=MIN_REL, min_score=0.0)
    if not cand:
        return []
    if not use_llm:
        return [(s, e) for s, e in cand[:k]]
    texts = [e["text"] for _, e in cand]
    try:
        idx = _llm_pick(query, texts)
    except Exception:
        idx = []
    if idx:
        return [(cand[i][0], cand[i][1]) for i in idx]
    if fallback:
        return [cand[0]]
    return []
