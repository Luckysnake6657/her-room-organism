# -*- coding: utf-8 -*-
"""统计推断：给已有数据补上区间与效应量。

- 3c：每个判读者的 rho + bootstrap 95% CI；三读者 ICC(2,1)
- BDI：12/20 的 Wilson 区间
- P0b：多种子 std vs dense 的效应量 + bootstrap CI
- 消融：full vs 各 lesion 的生病分钟效应量
"""
import json
import random

import numpy as np
from scipy import stats

from .sim import Sim

SEEDS = (1, 2, 3, 4, 5)


def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return float((c - h) / d), float((c + h) / d)


def three_c():
    key = json.load(open("evidence/p3/three_condition/key.json", encoding="utf-8-sig"))["A"]
    items = {i["idx"]: i for i in key}
    readers = []
    for f in ("reader.json", "r2.json", "r3.json"):
        r = json.load(open("evidence/p3/three_condition/" + f, encoding="utf-8-sig"))
        readers.append({x["idx"]: x["score"] for x in r["A"]})
    idx = [i for i in items if items[i]["state"] in ("good", "mild", "bad")
           and not items[i].get("dup")]
    D = np.array([items[i]["D"] for i in idx])
    mat = np.array([[r.get(i, np.nan) for i in idx] for r in readers], dtype=float)
    rhos, cis = [], []
    rng = random.Random(20261029)
    for row in mat:
        rho = stats.spearmanr(row, D).statistic
        bs = []
        for _ in range(2000):
            pick = [rng.randrange(len(idx)) for _ in idx]
            bs.append(stats.spearmanr(row[pick], D[pick]).statistic)
        rhos.append(float(rho))
        finite = [x for x in bs if np.isfinite(x)]
        if len(finite) >= 100:
            cis.append((float(np.percentile(finite, 2.5)),
                        float(np.percentile(finite, 97.5))))
        else:
            cis.append((float("nan"), float("nan")))

    # ICC(2,1)
    n, k = mat.shape
    grand = mat.mean()
    msr = k * ((mat.mean(axis=1) - grand) ** 2).sum() / (n - 1)
    msc = n * ((mat.mean(axis=0) - grand) ** 2).sum() / (k - 1)
    sse = ((mat - mat.mean(axis=1, keepdims=True) - mat.mean(axis=0, keepdims=True)
            + grand) ** 2).sum()
    mse = sse / ((n - 1) * (k - 1))
    icc21 = (msr - mse) / (msr + (k - 1) * mse + k * (msc - mse) / n)
    icc2k = (msr - mse) / (msr + (msc - mse) / n)
    icc31 = (msr - mse) / (msr + (k - 1) * mse)
    return dict(n=len(idx), rhos=rhos, ci=cis,
                icc21=float(icc21), icc2k=float(icc2k), icc31=float(icc31))


def p0b():
    out = {}
    for label, ch in (("std", False), ("dense", "dense")):
        sick, threats = [], []
        for s in SEEDS:
            sim = Sim(s, (), s, "allostatic", 30, product=True, challenge=ch)
            sim.run()
            sick.append(sim.stats["sick"])
            threats.append(sim.stats["threats"])
        out[label] = dict(sick=sick, threats=threats,
                          sick_mean=float(np.mean(sick)), sick_sd=float(np.std(sick, ddof=1)))
    pooled = np.sqrt(((np.var(out["std"]["sick"], ddof=1) +
                       np.var(out["dense"]["sick"], ddof=1)) / 2))
    d = (out["dense"]["sick_mean"] - out["std"]["sick_mean"]) / pooled if pooled else 0.0
    diff = [b - a for a, b in zip(out["std"]["sick"], out["dense"]["sick"])]
    rng = random.Random(7)
    bs = [np.mean([rng.choice(diff) for _ in diff]) for _ in range(2000)]
    out["effect"] = dict(cohens_d=float(d), diff_mean=float(np.mean(diff)),
                         diff_ci=(float(np.percentile(bs, 2.5)),
                                  float(np.percentile(bs, 97.5))))
    return out


def ablation():
    """20 seed；主结局改成"自我照料"（吃饭+社交），不吃免疫判定。"""
    seeds = tuple(range(1, 21))

    def score(sim):
        return sim.stats["meals"] + sim.stats["socials"]

    full = []
    sick_full = []
    for s in seeds:
        sim = Sim(s, (), s, "allostatic", 30, product=True)
        sim.run()
        full.append(score(sim))
        sick_full.append(sim.stats["sick"])
    full = np.array(full, dtype=float)
    res = {}
    rng = random.Random(11)
    for lesion in ("energy", "stress", "sleep", "lonely", "immune", "clock"):
        vals, sick = [], []
        for s in seeds:
            sim = Sim(s, (lesion,), s, "allostatic", 30, product=True)
            sim.run()
            vals.append(score(sim))
            sick.append(sim.stats["sick"])
        arr = np.array(vals, dtype=float)
        pooled = np.sqrt((full.var(ddof=1) + arr.var(ddof=1)) / 2)
        d = (arr.mean() - full.mean()) / pooled if pooled else 0.0
        diff = arr - full
        bs = [np.mean([rng.choice(diff) for _ in diff]) for _ in range(2000)]
        res[lesion] = dict(mean=float(arr.mean()), sd=float(arr.std(ddof=1)),
                           d=float(d), vals=vals,
                           diff_ci=(float(np.percentile(bs, 2.5)),
                                    float(np.percentile(bs, 97.5))),
                           sick_mean=float(np.mean(sick)))
    return dict(full=dict(mean=float(full.mean()), sd=float(full.std(ddof=1)),
                          vals=full.tolist(), sick_mean=float(np.mean(sick_full))),
                lesions=res)


def main():
    out = dict(three_c=three_c(), bdi=dict(n=20, k=12,
                                           ci=wilson(12, 20)),
               p0b=p0b(), ablation=ablation())
    json.dump(out, open("evidence/p3/testbed_stats.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(dict(three_c_rho=out["three_c"]["rhos"],
                          three_c_icc=(round(out["three_c"]["icc21"], 3),
                                       round(out["three_c"]["icc2k"], 3),
                                       round(out["three_c"]["icc31"], 3)),
                          bdi_ci=[round(x, 3) for x in out["bdi"]["ci"]],
                          p0b_d=round(out["p0b"]["effect"]["cohens_d"], 2),
                          ablation={k: round(v["d"], 2) for k, v in out["ablation"]["lesions"].items()}),
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
