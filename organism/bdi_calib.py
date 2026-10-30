# -*- coding: utf-8 -*-
"""BDI 置信校准：自报 confidence 能不能预测"抽对了"。

方法：40 条真实消息 × 2 次抽取；独立判读者逐字段判"是否被消息支持"；
AUC/ECE + 打乱对照。
"""
import json
import random
import re

import numpy as np
from sklearn.metrics import roc_auc_score

from . import api_client

JUDGE = """消息：%s

抽取结果：
activity: %s
desire: %s
belief: %s
mood: %s

逐项判断"是否被消息直接支持"（能直接看出=yes，猜的/没有=no）。只输出 JSON：
{"activity": true/false, "desire": true/false, "belief": true/false, "mood": true/false}"""


def ece(p, y, bins=5):
    p, y = np.array(p), np.array(y)
    edges = np.linspace(0, 1, bins + 1)
    tot = 0.0
    for i in range(bins):
        m = (p >= edges[i]) & (p < edges[i + 1] if i < bins - 1 else p <= edges[i + 1])
        if m.sum():
            tot += m.sum() * abs(p[m].mean() - y[m].mean())
    return tot / len(p)


def main():
    msgs = []
    for line in open("evidence/p3/cmw_messages/messages.jsonl", encoding="utf-8"):
        d = json.loads(line)
        if d.get("isSelf") or not d.get("isOwner"):
            continue
        t = re.sub(r"\[[^\]]*\]", "", d.get("text") or "").strip()
        if 8 <= len(t) <= 60:
            msgs.append(t)
    rng = random.Random(11)
    msgs = list(dict.fromkeys(msgs))
    rng.shuffle(msgs)
    msgs = msgs[:40]
    from . import bdi
    rows = []
    for m in msgs:
        runs = [bdi.extract(m) for _ in range(2)]
        b = runs[0]
        nonempty = [k for k in bdi.FIELDS if b.get(k)]
        if not nonempty:
            continue
        try:
            raw = api_client.chat(JUDGE % (m, b.get("activity", ""), b.get("desire", ""),
                                           b.get("belief", ""), b.get("mood", "")),
                                  "", max_tokens=600, temperature=0.0)
        except Exception:
            continue
        mm = re.search(r"\{.*\}", raw, re.S)
        if not mm:
            continue
        try:
            verdict = json.loads(mm.group(0))
        except Exception:
            continue
        for k in nonempty:
            rows.append(dict(q=m, field=k, text=b.get(k), conf=float(b.get("confidence") or 0),
                             ok=bool(verdict.get(k)), conf2=float(runs[1].get("confidence") or 0)))
    if not rows:
        print("no rows")
        return
    y = [1 if r["ok"] else 0 for r in rows]
    s = [r["conf"] for r in rows]
    auc = roc_auc_score(y, s) if len(set(y)) > 1 else float("nan")
    out = dict(n=len(rows), fields=dict(
        activity=sum(1 for r in rows if r["field"] == "activity"),
        desire=sum(1 for r in rows if r["field"] == "desire"),
        belief=sum(1 for r in rows if r["field"] == "belief"),
        mood=sum(1 for r in rows if r["field"] == "mood")),
        acc=round(float(np.mean(y)), 3),
        auc=round(float(auc), 3),
        ece=round(float(ece(s, y)), 3),
        conf_mean=round(float(np.mean(s)), 3),
        conf_sd_between_runs=round(float(np.mean([abs(r["conf"] - r["conf2"]) for r in rows])), 3),
        rows=rows)
    json.dump(out, open("evidence/p3/bdi_calib.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps({k: out[k] for k in ("n", "acc", "auc", "ece", "conf_mean",
                                          "conf_sd_between_runs")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
