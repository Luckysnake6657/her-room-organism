# -*- coding: utf-8 -*-
"""BDI 逐字段置信：抽取时给每个字段单独打置信，再测校准。"""
import json
import random
import re

import numpy as np
from sklearn.metrics import roc_auc_score

from . import api_client

PROMPT = """只根据消息，输出 JSON：
{"activity": {"text": "...", "conf": 0.0}, "desire": {"text": "...", "conf": 0.0},
 "belief": {"text": "...", "conf": 0.0}, "mood": {"text": "...", "conf": 0.0}}
规则：只写能直接看出的；看不出 text 留空、conf=0；activity 不许写说话动作；mood 只在他明说时填；只输出 JSON。"""

JUDGE = """消息：%s

逐项判断"是否被消息直接支持"（能直接看出=yes）：
activity: %s
desire: %s
belief: %s
mood: %s

只输出 JSON：{"activity": true/false, "desire": true/false, "belief": true/false, "mood": true/false}"""


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
    msgs = list(dict.fromkeys(msgs))
    random.Random(11).shuffle(msgs)
    msgs = msgs[:40]
    rows = []
    for m in msgs:
        try:
            raw = api_client.chat(PROMPT, m, max_tokens=700, temperature=0.1)
        except Exception:
            continue
        mm = re.search(r"\{.*\}", raw, re.S)
        if not mm:
            continue
        try:
            d = json.loads(mm.group(0))
        except Exception:
            continue
        fields = {k: d.get(k, {}) for k in ("activity", "desire", "belief", "mood")}
        texts = {k: str((v or {}).get("text", "")).strip()[:40] for k, v in fields.items()}
        nonempty = [k for k in texts if texts[k]]
        if not nonempty:
            continue
        try:
            jr = api_client.chat(JUDGE % (m, texts["activity"], texts["desire"],
                                          texts["belief"], texts["mood"]),
                                 "", max_tokens=600, temperature=0.0)
            jm = re.search(r"\{.*\}", jr, re.S)
            verdict = json.loads(jm.group(0)) if jm else {}
        except Exception:
            continue
        for k in nonempty:
            rows.append(dict(q=m, field=k, text=texts[k],
                             conf=float((fields[k] or {}).get("conf") or 0),
                             ok=bool(verdict.get(k))))
    if not rows:
        print("no rows")
        return
    y = [1 if r["ok"] else 0 for r in rows]
    s = [r["conf"] for r in rows]
    auc = roc_auc_score(y, s) if len(set(y)) > 1 else float("nan")
    out = dict(n=len(rows), acc=round(float(np.mean(y)), 3),
               auc=round(float(auc), 3), ece=round(float(ece(s, y)), 3),
               conf_mean=round(float(np.mean(s)), 3), rows=rows)
    json.dump(out, open("evidence/p3/bdi_calib2.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps({k: out[k] for k in ("n", "acc", "auc", "ece", "conf_mean")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
