# -*- coding: utf-8 -*-
"""剩余科研的批量跑：威胁密度（P0b）+ words_base 定标。

3c 需要外部读者、向量检索需要模型，这两项不在这一次里。
"""
import json
import statistics as st

from . import corpus
from .sim import Sim


def density(days=30, seed=11):
    out = {}
    for label, ch in (("std", False), ("dense", "dense")):
        s = Sim(seed, (), seed, "allostatic", days, product=True, challenge=ch)
        s.run()
        a = [d["a_mean"] for d in s.daily if d.get("a_mean") is not None]
        out[label] = dict(
            stress=round(st.mean(a), 3) if a else None,
            sick_minutes=s.stats["sick"],
            threats=s.stats["threats"],
            missed=s.stats.get("missed_windows", 0),
            days=len(s.daily))
    return out


def words_base():
    pool = corpus.load()
    lens = sorted(len(t) for t in pool)
    return dict(n=len(lens), median=lens[len(lens) // 2] if lens else 0,
                p90=lens[int(len(lens) * 0.9)] if lens else 0)


if __name__ == "__main__":
    r = dict(density=density(), words=words_base())
    print(json.dumps(r, ensure_ascii=False, indent=2))
    json.dump(r, open("evidence/p3/research_batch.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
