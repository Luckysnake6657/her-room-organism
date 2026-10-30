# -*- coding: utf-8 -*-
"""BDI 抽取：他此刻在做什么 / 想要什么 / 以为的是什么。

只抽对话里**能直接看出**的；看不出来就留空（宁可空，不许猜）。
依据：Jafari et al., ACL Findings 2025（BDI 注入提升对齐，胜率 63%/67%）。
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor

from . import api_client

PROMPT = """只根据这段对话，输出一个 JSON：
{"joking": false, "activity": {"text": "...", "conf": 0.0}, "desire": {"text": "...", "conf": 0.0},
 "belief": {"text": "...", "conf": 0.0}, "mood": {"text": "...", "conf": 0.0}}
规则：
1. 先判断他是不是在**玩梗/反讽/开玩笑**；是的话 joking=true，四个字段全部留空、conf=0。
2. 只写对话里**能直接看出**的；看不出来 text 留空、conf=0。
3. activity 不许写"他在问/他在说/他在发消息"这类说话动作。
4. mood 只在他明说时填（烦/累/急/开心），不推测。
5. 不要编造；不确定就留空、conf 给低。
6. 只输出 JSON，不要解释。"""

FIELDS = ("activity", "desire", "belief", "mood")
MIN_CONF = 0.6


def _empty():
    return dict(activity="", desire="", belief="", mood="", confidence=0.0,
                confs={k: 0.0 for k in FIELDS})


def extract(text: str) -> dict:
    try:
        raw = api_client.chat(PROMPT, text, max_tokens=700, temperature=0.1)
    except Exception:
        return _empty()
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return _empty()
    try:
        d = json.loads(m.group(0))
    except Exception:
        return _empty()
    out = {"confs": {}, "joking": bool(d.get("joking"))}
    if out["joking"]:
        out.update({k: "" for k in FIELDS})
        out["confidence"] = 0.0
        out["confs"] = {k: 0.0 for k in FIELDS}
        return out
    for k in FIELDS:
        v = d.get(k)
        if isinstance(v, dict):
            text = str(v.get("text") or "").strip()[:40]
            conf = float(v.get("conf") or 0.0)
        else:
            text = str(v or "").strip()[:40]
            conf = float(d.get("confidence") or 0.0)
        out[k] = text
        out["confs"][k] = conf if text else 0.0
    confs = [out["confs"][k] for k in FIELDS if out[k]]
    out["confidence"] = round(sum(confs) / len(confs), 3) if confs else 0.0
    return out


def extract_many(texts, workers: int = 8) -> list:
    """并行抽取；抽取是无状态的，可以并发。"""
    with ThreadPoolExecutor(max_workers=workers) as ex:
        return list(ex.map(extract, texts))


def lines(bdi: dict) -> list:
    """只把非空且高置信的字段变成提示词。"""
    confs = bdi.get("confs") or {}
    out = []

    def ok(k):
        return bdi.get(k) and float(confs.get(k, bdi.get("confidence", 0))) >= MIN_CONF

    if ok("activity"):
        out.append("他现在在：%s" % bdi["activity"])
    if ok("desire"):
        out.append("他想要：%s" % bdi["desire"])
    if ok("belief"):
        out.append("他以为：%s" % bdi["belief"])
    if ok("mood"):
        out.append("他这会儿：%s" % bdi["mood"])
    return out
