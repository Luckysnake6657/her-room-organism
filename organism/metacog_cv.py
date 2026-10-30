# -*- coding: utf-8 -*-
"""元认知交叉验证：记忆消融造自然负例，20 次随机拆分，随机标签对照。

设计：
- 同一批自然问法（来自 quiz100_clean）
- 每次随机把一半"已确认事实"从本子里拿掉
- 拿掉的题 = 负例（本子没有），留下的题 = 正例
- 置信分对"本子有没有"的 AUC
- 20 次拆分 → 中位数/IQR；随机标签 → 对照 AUC≈0.5
"""
import json
import os
import random
import tempfile

import numpy as np
from sklearn.metrics import roc_auc_score

from . import notebook, retrieval


def ece(s, y, bins=5):
    s, y = np.array(s), np.array(y)
    edges = np.linspace(0, 1, bins + 1)
    tot = 0.0
    for i in range(bins):
        m = (s >= edges[i]) & (s < edges[i + 1] if i < bins - 1 else s <= edges[i + 1])
        if m.sum():
            tot += m.sum() * abs(s[m].mean() - y[m].mean())
    return tot / len(s)


def score_with(entries, questions):
    d = tempfile.mkdtemp()
    p = os.path.join(d, "nb.json")
    json.dump({"next": 100000, "entries": entries}, open(p, "w", encoding="utf-8"))
    nb = notebook.Notebook(p)
    out = []
    for q in questions:
        got = retrieval.retrieve(nb, q, k=5, min_rel=0.0, min_score=0.0)
        out.append(got[0][0] if got else 0.0)
    return out


def main():
    nb = notebook.Notebook("evidence/p3/cmw_native/notebook.json")
    entries = nb.entries
    facts = [e for e in entries if e.get("source") == "user_confirmed"
             and e["status"] != "deleted"]
    items = json.load(open("evidence/p3/quiz100_clean_data.json", encoding="utf-8"))
    by_fact = {}
    for it in items:
        if it.get("gold"):
            by_fact.setdefault(it["gold"], []).append(it["q"])
    facts = [e for e in facts if e["text"] in by_fact]
    questions, labels_base = [], []
    for e in facts:
        for q in by_fact[e["text"]]:
            questions.append((q, e["text"]))
    rng = random.Random(0)
    aucs, eces = [], []
    for seed in range(20):
        r = random.Random(seed)
        held = set(r.sample([e["text"] for e in facts], len(facts) // 2))
        kept_entries = [e for e in entries if e["text"] not in held]
        qs = [q for q, _ in questions]
        scores = score_with(kept_entries, qs)
        y = [0 if g in held else 1 for _, g in questions]
        if len(set(y)) < 2:
            continue
        aucs.append(roc_auc_score(y, scores))
        eces.append(ece(scores, y))
    # 对照：打乱标签
    ctrl = []
    for seed in range(20):
        r = random.Random(1000 + seed)
        held = set(r.sample([e["text"] for e in facts], len(facts) // 2))
        kept_entries = [e for e in entries if e["text"] not in held]
        scores = score_with(kept_entries, [q for q, _ in questions])
        y = [0 if g in held else 1 for _, g in questions]
        y2 = y[:]
        r.shuffle(y2)
        ctrl.append(roc_auc_score(y2, scores))
    out = dict(facts=len(facts), questions=len(questions), splits=len(aucs),
               auc_median=round(float(np.median(aucs)), 3),
               auc_iqr=[round(float(np.percentile(aucs, 25)), 3),
                        round(float(np.percentile(aucs, 75)), 3)],
               ece_median=round(float(np.median(eces)), 3),
               control_auc=round(float(np.median(ctrl)), 3),
               aucs=[round(a, 3) for a in aucs])
    json.dump(out, open("evidence/p3/metacog_cv.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps({k: out[k] for k in ("facts", "questions", "splits",
                                          "auc_median", "auc_iqr", "ece_median",
                                          "control_auc")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
