# -*- coding: utf-8 -*-
"""第三批：阈值权衡、形式统计版 3c、clock 语义。"""
import datetime as dt
import json
import re
import random

import numpy as np

from . import api_client, notebook, retrieval
from .sim import Sim

THRESH = (0.5, 0.3, 0.2)


def threshold_tradeoff():
    nb = notebook.Notebook("evidence/p3/cmw_import/notebook.json")
    rows = json.load(open("evidence/p3/retrieval_real200.json", encoding="utf-8"))["rows"]
    neg = ["我上周是不是说过要去看极光", "我的猫叫什么名字", "我什么时候说要换工作",
           "我对花生过敏吗", "我上次体检是哪天", "我借给谁钱了", "我的车停在哪",
           "我答应过谁什么", "我生日是哪天", "我在哪家公司上班"]
    out = {}
    for th in THRESH:
        gold5 = top1 = 0
        for r in rows:
            got = retrieval.retrieve(nb, r["query"], k=5, min_rel=th, min_score=0.0)
            texts = [x["text"] for _, x in got]
            sims = [1.0 if t == r["expected"] else 0.0 for t in texts]
            gold5 += int(any(s > 0 for s in sims))
            top1 += int(bool(sims) and sims[0] > 0)
        neg_counts = [len(retrieval.retrieve(nb, q, k=5, min_rel=th, min_score=0.0))
                      for q in neg]
        out[str(th)] = dict(gold5=gold5, top1=top1, n=len(rows),
                            neg_mean=float(np.mean(neg_counts)))
    return out


STAT_PROMPT = """这是一段聊天里“她”的回复的统计特征（不含内容、不含时间）：
回复条数：%d
总字数：%d
平均每条字数：%.1f
句号/问号/省略号/感叹号：%d/%d/%d/%d

判断她当时的身体状态更像：good / mild / bad。只输出一个词。"""


def form_stats():
    base = "evidence/p3/three_condition"
    key = {i["idx"]: i for i in json.load(open(base + "/key.json", encoding="utf-8-sig"))["A"]}
    text = open(base + "/A_full.txt", encoding="utf-8").read()
    parts = re.split(r"第\s*(\d+)\s*段", text)
    rows = []
    for i in range(1, len(parts), 2):
        idx = int(parts[i])
        lines = [l.strip() for l in parts[i + 1].splitlines() if l.strip()]
        hers = [l for l in lines if l.startswith("她")]
        if not hers:
            continue
        chars = [len(x) for x in hers]
        p = "".join(hers)
        feats = (len(hers), sum(chars), sum(chars) / len(chars),
                 p.count("。"), p.count("？"), p.count("…"), p.count("！"))
        scores = []
        for _ in range(3):
            try:
                raw = api_client.chat(STAT_PROMPT % feats, "", max_tokens=800, temperature=0.7)
            except Exception:
                raw = ""
            w = raw.strip().lower()
            scores.append(2 if "good" in w else (1 if "mild" in w else (0 if "bad" in w else 1)))
        rows.append((idx, float(np.mean(scores))))
    from scipy import stats
    xs = [s for i, s in rows if i in key]
    ys = [key[i]["D"] for i, _ in rows if i in key]
    rho = stats.spearmanr(xs, -np.array(ys)).statistic if len(set(xs)) > 1 else float("nan")
    return dict(n=len(xs), rho=float(rho), rows=rows)


def clock_semantics():
    def states(lesion=None):
        out = []
        for s in range(1, 21):
            sim = Sim(s, (lesion,) if lesion else (), s, "allostatic", 5, product=True)
            sim.run()
            b = sim.body
            out.append(dict(energy=b.e, sleep=b.s, stress=b.a, immune=b.i,
                            lonely=b.l, phi=b.phi))
        return out

    base = states()
    cur = states("clock")
    ds = {}
    for k in base[0]:
        a = np.array([x[k] for x in base], dtype=float)
        b = np.array([x[k] for x in cur], dtype=float)
        pooled = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2) or 1e-9
        ds[k] = float((b.mean() - a.mean()) / pooled)
    rank = sorted(ds, key=lambda k: -abs(ds[k]))
    return dict(ds=ds, rank=rank, phi_rank=rank.index("phi") + 1)


def main():
    out = {}
    for name, fn in (("threshold", threshold_tradeoff),
                     ("form_stats", form_stats),
                     ("clock", clock_semantics)):
        try:
            out[name] = fn()
        except Exception as e:
            out[name] = dict(error=str(e))
    json.dump(out, open("evidence/p3/extra_experiments3.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
