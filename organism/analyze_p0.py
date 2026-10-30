# -*- coding: utf-8 -*-
"""P0 分析：消融是否让行为变形（配对检验）+ 行为能否解码出「拆了哪个系统」。

统计口径在 docs/p0-prereg.md 里先写死，这里只实现，不调参。

距离的定义（重要）
------------------
先把每个行为特征按「同一模型、不同政策噪声」的配对差（baseline - null）估出噪声 SD，
再用这个 SD 归一化：z = (cond - baseline) / sd_null。
距离 = sqrt(mean(z^2))，即「平均而言偏离了噪声的几倍」。
这样，天生波动大的特征不会淹没稳定的效应。
"""
import argparse
import json
import os

import numpy as np

from . import params as P
from .render import check_no_numbers

CONDS = ("baseline", "null", "cosmetic", "shuffle",
         "lesion_energy", "lesion_sleep", "lesion_stress",
         "lesion_immune", "lesion_lonely", "lesion_clock")
LESIONS = tuple(c for c in CONDS if c.startswith("lesion_"))
SD_FLOOR = 0.05


def load(path):
    recs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    return recs


def index(recs):
    return {(r["cond"], r["seed"]): r for r in recs}


def matrix(idx, cond, seeds):
    return np.array([idx[(cond, s)]["features"] for s in seeds], dtype=float)


def perm_paired(d_a, d_b, n_perm=P.N_PERM, seed=0):
    """配对置换：每个种子里 d_a 与 d_b 可交换。"""
    obs = float(d_a.mean() - d_b.mean())
    rs = np.random.default_rng(seed)
    n = len(d_a)
    cnt = 0
    for _ in range(n_perm):
        swap = rs.random(n) < 0.5
        x = np.where(swap, d_b, d_a)
        y = np.where(swap, d_a, d_b)
        if x.mean() - y.mean() >= obs:
            cnt += 1
    return obs, (cnt + 1.0) / (n_perm + 1.0)


def classify_loso(idx, seeds, classes, key="z"):
    correct = total = 0
    for s in seeds:
        cent = {c: np.mean([idx[(c, s2)][key] for s2 in seeds if s2 != s], axis=0)
                for c in classes}
        for c in classes:
            v = idx[(c, s)][key]
            pred = min(classes, key=lambda cc: float(np.sum((cent[cc] - v) ** 2)))
            correct += int(pred == c)
            total += 1
    return correct / total


def perm_classify(idx, seeds, classes, n_perm=1000, seed=0):
    base = classify_loso(idx, seeds, classes)
    rs = np.random.default_rng(seed)
    null = []
    for _ in range(n_perm):
        for s in seeds:
            vals = [idx[(c, s)]["z"] for c in classes]
            order = rs.permutation(len(classes))
            for c, k in zip(classes, order):
                idx[(c, s)]["z"] = vals[k]
        null.append(classify_loso(idx, seeds, classes))
    val = float((np.sum(np.array(null) >= base) + 1) / (n_perm + 1))
    return base, val, float(np.mean(null))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="evidence/p0")
    ap.add_argument("--perm", type=int, default=P.N_PERM)
    ap.add_argument("--cls-perm", type=int, default=1000)
    ap.add_argument("--suffix", default="", help="条件名后缀，如 _c 表示挑战周")
    args = ap.parse_args(argv)

    recs = load(os.path.join(args.out, "runs.jsonl"))
    idx = index(recs)
    seeds = sorted({r["seed"] for r in recs})
    conds = tuple(c + args.suffix for c in CONDS if (c + args.suffix, seeds[0]) in idx)
    assert all((c, s) in idx for c in conds for s in seeds), "runs 不完整"

    Fb = matrix(idx, "baseline" + args.suffix, seeds)
    Fn = matrix(idx, "null" + args.suffix, seeds)
    sd_null = np.maximum(np.std(Fn - Fb, axis=0, ddof=1), SD_FLOOR)

    for (c, s), r in idx.items():
        r["z"] = (np.array(r["features"], dtype=float) - Fb[seeds.index(s)]) / sd_null

    def dists(cond):
        z = (matrix(idx, cond, seeds) - Fb) / sd_null
        return np.sqrt(np.mean(z ** 2, axis=1))

    print("== baseline ==")
    surv = np.mean([idx[("baseline" + args.suffix, s)]["survived"] for s in seeds])
    days = np.mean([idx[("baseline" + args.suffix, s)]["days_alive"] for s in seeds])
    print("survived %.3f  mean_days %.3f  (n=%d seeds)" % (surv, days, len(seeds)))
    print("feature null-sd: " + ", ".join(
        "%s=%.2f" % (n, s) for n, s in zip(P.FEATURE_NAMES, sd_null)))

    print("\n== criterion 1: does removing a system deform behavior? ==")
    print("%-15s %8s %8s %8s %10s %10s %6s" % (
        "condition", "d_les", "d_null", "ratio", "p", "p_bonf", "death"))
    rows = {}
    d_null = dists("null" + args.suffix)
    for c in LESIONS:
        cn = c + args.suffix
        d_les = dists(cn)
        obs, p = perm_paired(d_les, d_null, args.perm, seed=sum(ord(x) for x in cn))
        deaths = np.mean([idx[(cn, s)]["death"] is not None for s in seeds])
        rows[c] = dict(d_les=float(d_les.mean()), d_null=float(d_null.mean()),
                       ratio=float(d_les.mean() / max(1e-9, d_null.mean())),
                       p=p, p_bonf=float(min(1.0, p * 6)), deaths=float(deaths))
        print("%-15s %8.3f %8.3f %8.2f %10.4f %10.4f %6.2f" % (
            c, d_les.mean(), d_null.mean(), d_les.mean() / d_null.mean(),
            p, min(1.0, p * 6), deaths))

    print("\n== controls ==")
    print("cosmetic mean d=%.4f (expect 0)  shuffle mean d=%.3f  null mean d=%.3f" % (
        dists("cosmetic" + args.suffix).mean(), dists("shuffle" + args.suffix).mean(),
        d_null.mean()))

    print("\n== criterion 3b: can behavior decode which system was removed? ==")
    acc, p_acc, null_acc = perm_classify(idx, seeds, LESIONS, args.cls_perm, seed=7)
    print("LODO 6-way acc=%.3f  perm p=%.4f  null_acc=%.3f  (chance=%.3f)" % (
        acc, p_acc, null_acc, 1 / 6))

    print("\n== criterion 3a: digits/units in rendered text ==")
    bad = []
    tdir = os.path.join(args.out, "transcripts")
    if os.path.isdir(tdir):
        for fn in sorted(os.listdir(tdir)):
            with open(os.path.join(tdir, fn), encoding="utf-8") as f:
                hits = check_no_numbers(f.read())
            if hits:
                bad.append((fn, hits[:3]))
    print("transcripts=%d  violations=%d %s" % (
        len(os.listdir(tdir)) if os.path.isdir(tdir) else 0, len(bad), bad[:3]))

    print("\n== per-lesion top features (mean z) ==")
    for c in LESIONS:
        z = (matrix(idx, c + args.suffix, seeds) - Fb) / sd_null
        mz = z.mean(axis=0)
        order = np.argsort(-np.abs(mz))[:3]
        print("%-15s %s" % (c, ", ".join("%s %+.2f" % (P.FEATURE_NAMES[i], mz[i]) for i in order)))

    summary = dict(kind=args.suffix or "normal", n_seeds=len(seeds),
                   baseline_survived=float(surv), baseline_days=float(days),
                   null_distance=float(d_null.mean()),
                   cosmetic_distance=float(dists("cosmetic" + args.suffix).mean()),
                   shuffle_distance=float(dists("shuffle" + args.suffix).mean()),
                   lesions=rows, decode_acc=float(acc), decode_p=float(p_acc),
                   decode_null=float(null_acc), no_number_violations=len(bad))
    with open(os.path.join(args.out, "summary%s.json" % args.suffix), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
