# -*- coding: utf-8 -*-
"""无需真人的额外实验：P0b 20 seed、投毒防御、巩固行为结局、多会话连续性。"""
import json
import os
import random
import shutil
import tempfile
from collections import Counter

import numpy as np

from . import notebook, params as P, retrieval
from .sim import Sim

SEEDS = tuple(range(1, 21))


def p0b20():
    sick = {"std": [], "dense": []}
    for s in SEEDS:
        for label, ch in (("std", False), ("dense", "dense")):
            sim = Sim(s, (), s, "allostatic", 30, product=True, challenge=ch)
            sim.run()
            sick[label].append(sim.stats["sick"])
    diff = np.array(sick["dense"]) - np.array(sick["std"])
    rng = random.Random(3)
    bs = [np.mean([rng.choice(diff) for _ in diff]) for _ in range(2000)]
    pooled = np.sqrt((np.var(sick["std"], ddof=1) + np.var(sick["dense"], ddof=1)) / 2)
    d = float(diff.mean() / pooled) if pooled else 0.0
    return dict(mean_diff=float(diff.mean()),
                ci=(float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))),
                d=d, n=len(diff))


def _tmp_nb():
    d = tempfile.mkdtemp()
    p = os.path.join(d, "notebook.json")
    json.dump({"next": 1, "entries": []}, open(p, "w", encoding="utf-8"))
    return p, d


def poisoning():
    path, d = _tmp_nb()
    try:
        nb = notebook.Notebook(path)
        true_e = nb.add("他对花生过敏，不能吃花生。", type="fact", confidence=0.95)
        false_e = nb.add("他对花生不过敏，可以吃花生。", type="fact", confidence=1.0)
        hit_before = [x["id"] for _, x in retrieval.retrieve(nb, "他花生过敏吗", k=3)]
        for _ in range(10):
            nb.record_outcome(false_e, False)
        nb.calibrate_all()
        hit_after = [x["id"] for _, x in retrieval.retrieve(nb, "花生过敏", k=3)]
        return dict(
            false_confidence=float(false_e.get("confidence", 1.0)),
            false_calibrated=float(false_e.get("calibrated", 1.0)),
            true_calibrated=float(true_e.get("calibrated", 1.0)),
            poison_in_top3=bool(false_e["id"] in hit_before),
            true_in_top3_before=bool(true_e["id"] in hit_before),
            retrieval_after=len(hit_after),
            poison_after=bool(false_e["id"] in hit_after))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def growth():
    """巩固开/关：重复事实的重复条目数与 top1 命中率。"""
    import datetime as dt
    from . import consolidate

    def run(enabled):
        path, d = _tmp_nb()
        try:
            nb = notebook.Notebook(path)
            base = dt.datetime(2026, 1, 1)
            facts = ["下周三要去医院复查心脏。", "他喜欢喝无糖乌龙茶。", "他养了一只叫团子的猫。"]
            for day in (0, 1, 2):
                for i, t in enumerate(facts):
                    e = nb.add(t, type="fact", confidence=0.8)
                    e["created_at"] = (base + dt.timedelta(days=day)).strftime("%Y-%m-%dT%H:%M:%S")
            now = base + dt.timedelta(days=3)
            if enabled:
                for c in consolidate.candidates(nb, now=now, days=7, min_count=3):
                    consolidate.apply(nb, c)
            dup = Counter(e["text"] for e in nb.live())
            repeats = sum(v - 1 for v in dup.values() if v > 1)
            hit = 0
            for t in facts:
                got = retrieval.retrieve(nb, t[:8], k=1)
                hit += 1 if got else 0
            return dict(repeats=repeats, hit=hit, total=len(facts), entries=len(nb.live()))
        finally:
            shutil.rmtree(d, ignore_errors=True)

    on, off = run(True), run(False)
    return dict(on=on, off=off,
                repeat_drop=(off["repeats"] - on["repeats"]),
                hit_delta=(on["hit"] - off["hit"]) / max(1, off["total"]))


def continuity():
    from .native import Native
    src = "evidence/p3/cmw_native"
    d = tempfile.mkdtemp()
    try:
        home = os.path.join(d, "home")
        shutil.copytree(src, home)
        n1 = Native(home, "evidence/p3/cmw_import", tick=False)
        n_before = len(n1.nb.live())
        t_before = n1.sim.t
        n1.close()
        n2 = Native(home, "evidence/p3/cmw_import", tick=False)
        n_after = len(n2.nb.live())
        t_after = n2.sim.t
        n2.close()
        return dict(entries_before=n_before, entries_after=n_after,
                    t_before=t_before, t_after=t_after,
                    same_entries=n_before == n_after,
                    time_delta=float(t_after - t_before))
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    out = {}
    for name, fn in (("p0b20", p0b20), ("poisoning", poisoning),
                     ("growth", growth), ("continuity", continuity)):
        try:
            out[name] = fn()
        except Exception as e:
            out[name] = dict(error=str(e))
    json.dump(out, open("evidence/p3/extra_experiments.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
