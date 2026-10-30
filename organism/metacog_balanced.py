# -*- coding: utf-8 -*-
"""平衡集：40 有答案 + 40 无答案（含 14 条近似错例），测元认知敏感度/校准。"""
import difflib
import json

import numpy as np
from sklearn.metrics import roc_auc_score

from . import notebook, retrieval

ABSENT = ["我猫叫什么名字？", "我生日是哪天？", "我车停在哪？", "我上次体检是哪天？",
          "我借给谁钱了？", "我表弟叫什么？", "我住在哪？", "我手机号尾号多少？",
          "我上次去杭州住哪？", "我什么时候搬的家？", "我买的显示器多大？",
          "我上次跑步跑了几公里？", "我哪天请的假？", "我体检报告放哪了？",
          "我什么时候说要去北京？", "我存的钱够买什么？", "我上次去成都是哪天？",
          "我养过什么宠物？", "我上次旅行去哪？", "我买过最贵的东西是什么？",
          "我最好的朋友叫什么？", "我驾照考了吗？", "我四级过了吗？", "我导师叫什么？",
          "我宿舍几号楼？", "我什么时候放寒假？"]
HARD = ["我 S26 赛季打了几场？", "我历史一共打了 296 场？", "我 S24 最高 1791 分？",
        "我 Rating 1.15？", "我 KD 1.24？", "我胜率 52%？", "我用的是小米手机？",
        "我想拉小6一起去？", "我搜过量子计算吗？", "我用过 Midjourney 吗？",
        "我给对方发过漫画文件？", "我现在在纠结考公还是工作？",
        "我说话句子长、很少语气词？", "我 S23 赛季打了多少场？"]


def main():
    nb = notebook.Notebook("evidence/p3/cmw_native/notebook.json")
    rows = json.load(open("evidence/p3/retrieval_real200.json", encoding="utf-8"))["rows"]
    pos = []
    for r in rows:
        got = retrieval.retrieve(nb, r["query"], k=3, min_rel=0.0, min_score=0.0)
        if got and any(difflib.SequenceMatcher(None, e["text"], r["expected"]).ratio() > 0.85
                       for _, e in got):
            pos.append(r["query"])
        if len(pos) >= 40:
            break
    trials = []
    for q in pos:
        got = retrieval.retrieve(nb, q, k=5, min_rel=0.0, min_score=0.0)
        trials.append((q, 1, got[0][0] if got else 0.0))
    for q in ABSENT + HARD:
        got = retrieval.retrieve(nb, q, k=5, min_rel=0.0, min_score=0.0)
        trials.append((q, 0, got[0][0] if got else 0.0))
    y = np.array([t[1] for t in trials])
    s = np.array([t[2] for t in trials])
    auc = roc_auc_score(y, s)
    edges = np.linspace(0, 1, 6)
    ece = 0.0
    for i in range(5):
        lo, hi = edges[i], edges[i + 1]
        m = (s >= lo) & (s < hi if i < 4 else s <= hi)
        if m.sum():
            ece += m.sum() * abs(s[m].mean() - y[m].mean())
    ece /= len(s)
    out = dict(n=len(trials), pos=int(y.sum()), neg=int((1 - y).sum()),
               auc=round(float(auc), 3), ece=round(float(ece), 3),
               brier=round(float(np.mean((s - y) ** 2)), 3),
               trials=[dict(q=t[0], y=t[1], score=round(t[2], 3)) for t in trials])
    json.dump(out, open("evidence/p3/metacog_balanced.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps({k: out[k] for k in ("n", "pos", "neg", "auc", "ece", "brier")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
