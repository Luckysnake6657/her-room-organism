# -*- coding: utf-8 -*-
"""可读性审计：一个系统被拆掉之后，**文本上**有多少天看得出来。

3b 测的是"特征空间能不能分辨"，3c 测的是"人能不能看出来"。
这个脚本补中间那一层：把消融后的逐日文本与同种子的基线逐日比对，
数「完全一样的天数」和「平均字面相似度」。

一个系统可能：
  - 特征上很响、文本上很静 → 是渲染/粒度问题（改文本或加长窗口）
  - 特征上也静 → 是这个世界里它本来就没被用到（改世界，比如密集威胁）
"""
import argparse
import difflib
import json
import os

from . import params as P
from .render import render_run
from .sim import Sim

LESIONS = (("energy", ("energy",)),
           ("sleep", ("sleep",)),
           ("stress", ("stress",)),
           ("immune", ("immune",)),
           ("lonely", ("lonely",)),
           ("clock", ("clock",)))


def day_texts(res, seed, days):
    """按天切：渲染整段再按空行分，保证和用户看到的一致。"""
    text = render_run(res, seed, days)
    parts = [p.strip() for p in text.split("\n\n") if p.strip()]
    return parts


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="3,4,5")
    ap.add_argument("--days", type=int, default=5)
    ap.add_argument("--out", default="evidence/p0/readability.json")
    args = ap.parse_args(argv)
    seeds = [int(x) for x in args.seeds.split(",")]

    rows = {}
    for name, lesion in LESIONS:
        ident, ratios = [], []
        for s in seeds:
            base = Sim(s, (), P.MAIN_NOISE_BASE + s, "allostatic", P.DAYS).run()
            les = Sim(s, lesion, P.MAIN_NOISE_BASE + s, "allostatic", P.DAYS).run()
            tb = day_texts(base, s, args.days)
            tl = day_texts(les, s, args.days)
            n = min(len(tb), len(tl))
            for i in range(n):
                ident.append(1.0 if tb[i] == tl[i] else 0.0)
                ratios.append(difflib.SequenceMatcher(None, tb[i], tl[i]).ratio())
        rows[name] = dict(identical_frac=sum(ident) / max(1, len(ident)),
                          mean_similarity=sum(ratios) / max(1, len(ratios)),
                          n_days=len(ident))
        print("%-8s identical_days=%4.1f%%  mean_similarity=%.3f  (n=%d day-pairs)" % (
            name, 100 * rows[name]["identical_frac"], rows[name]["mean_similarity"],
            rows[name]["n_days"]))

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
