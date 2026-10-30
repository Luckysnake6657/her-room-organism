# -*- coding: utf-8 -*-
"""E10b：50 条合成形式统计（由身体状态生成），测“统计特征能否解码状态”。

明确：这是合成校准，不是真实文本；只回答“给定我们的形式映射，统计量是否可读”。
"""
import json
import random

import numpy as np

from . import api_client, form
from .sim import Sim

PROMPT = """这是一段聊天里“她”的回复的统计特征（不含内容、不含时间）：
回复条数：%d
总字数：%d
平均每条字数：%.1f
句号/问号/省略号/感叹号：%d/%d/%d/%d

判断她当时的身体状态更像：good / mild / bad。只输出一个词。"""


def main():
    rng = random.Random(20261029)
    rows = []
    for seed in range(1, 6):
        sim = Sim(seed, (), seed, "allostatic", 20, product=True)
        sim.run()
        for d in sim.daily[:10]:
            b = sim.body
            f = form.form_of(b)
            words = max(12, min(180, int(f["words"] * rng.uniform(0.8, 1.2))))
            msgs = max(1, min(4, 1 + words // 30))
            punct = (msgs, 1 if b.a > 0.6 else 0,
                     1 if words < 20 else 0, 0)
            feats = (msgs, words, words / msgs, punct[0], punct[1], punct[2], punct[3])
            scores = []
            for _ in range(3):
                try:
                    raw = api_client.chat(PROMPT % feats, "", max_tokens=800, temperature=0.7)
                except Exception:
                    raw = ""
                w = raw.strip().lower()
                scores.append(2 if "good" in w else (1 if "mild" in w else (0 if "bad" in w else 1)))
            rows.append(dict(D=float(b.D()), score=float(np.mean(scores)), words=words))
    from scipy import stats
    xs = [r["score"] for r in rows]
    ys = [-r["D"] for r in rows]
    rho = stats.spearmanr(xs, ys).statistic
    r = random.Random(3)
    bs = []
    for _ in range(2000):
        idx = [r.randrange(len(rows)) for _ in rows]
        v = stats.spearmanr([xs[i] for i in idx], [ys[i] for i in idx]).statistic
        if np.isfinite(v):
            bs.append(v)
    out = dict(n=len(rows), rho=float(rho),
               ci=(float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))),
               rows=rows)
    json.dump(out, open("evidence/p3/form_stats50.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(dict(n=out["n"], rho=round(out["rho"], 3),
                          ci=[round(x, 3) for x in out["ci"]]), ensure_ascii=False))


if __name__ == "__main__":
    main()
