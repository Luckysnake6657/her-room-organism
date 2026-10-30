# -*- coding: utf-8 -*-
"""无需真人的第二批：U 可辨识性、消融语义、巩固归档、3c 去泄漏。"""
import datetime as dt
import json
import math
import os
import random
import re
import shutil
import tempfile
from collections import Counter

import numpy as np

from . import consolidate, notebook, params as P, retrieval
from .sim import Sim


# E5 -----------------------------------------------------------------
def u_identifiability():
    u_max = float(P.U_MAX)
    true_hl = float(P.U_HALF_LIFE_DAYS)
    rng = random.Random(20261029)

    def u_after(days):
        return u_max * (1.0 - 0.5 ** (days / true_hl))

    def estimate(obs, days):
        best, best_err = None, 1e9
        for hl in np.arange(0.5, 60.0, 0.01):
            pred = u_max * (1.0 - 0.5 ** (days / hl))
            err = (pred - obs) ** 2
            if err < best_err:
                best, best_err = float(hl), err
        return best

    out = {}
    for days in (7, 14, 30):
        ests = []
        for _ in range(1000):
            obs = max(0.0, u_after(days) + rng.gauss(0, 0.05))
            ests.append(estimate(obs, days))
        ests = np.array(ests)
        out[str(days)] = dict(
            mean=float(ests.mean()),
            ci=(float(np.percentile(ests, 2.5)), float(np.percentile(ests, 97.5))),
            rel_err=float(abs(ests.mean() - true_hl) / true_hl),
        )
    return out


# E6 -----------------------------------------------------------------
def _final_states(sim):
    b = sim.body
    return dict(energy=b.e, sleep=b.s, stress=b.a, immune=b.i, lonely=b.l)


def ablation_semantics():
    seeds = tuple(range(1, 21))

    def run(lesion=None):
        vals = []
        for s in seeds:
            sim = Sim(s, (lesion,) if lesion else (), s, "allostatic", 5, product=True)
            sim.run()
            vals.append(_final_states(sim))
        return vals

    base = run()
    res = {}
    for lesion in ("energy", "stress", "sleep", "lonely", "immune", "clock"):
        cur = run(lesion)
        target = {"energy": "energy", "stress": "stress", "sleep": "sleep",
                  "lonely": "lonely", "immune": "immune", "clock": "energy"}[lesion]
        ds = {}
        for k in base[0]:
            a = np.array([x[k] for x in base], dtype=float)
            b = np.array([x[k] for x in cur], dtype=float)
            pooled = np.sqrt((a.var(ddof=1) + b.var(ddof=1)) / 2) or 1e-9
            ds[k] = float((b.mean() - a.mean()) / pooled)
        rank = sorted(ds, key=lambda k: -abs(ds[k]))
        res[lesion] = dict(target=target, ds=ds, rank=rank,
                           target_rank=rank.index(target) + 1)
    return res


# E7 -----------------------------------------------------------------
def consolidation_archive():
    def run(archive):
        d = tempfile.mkdtemp()
        try:
            p = os.path.join(d, "nb.json")
            json.dump({"next": 1, "entries": []}, open(p, "w", encoding="utf-8"))
            nb = notebook.Notebook(p)
            base = dt.datetime(2026, 1, 1)
            facts = ["下周三要去医院复查心脏。", "他喜欢喝无糖乌龙茶。", "他养了一只叫团子的猫。"]
            sources = []
            for day in (0, 1, 2):
                for t in facts:
                    e = nb.add(t, type="fact", confidence=0.8)
                    e["created_at"] = (base + dt.timedelta(days=day)).strftime("%Y-%m-%dT%H:%M:%S")
                    sources.append(e)
            now = base + dt.timedelta(days=3)
            applied = 0
            for c in consolidate.candidates(nb, now=now, days=7, min_count=3):
                if consolidate.apply(nb, c):
                    applied += 1
            if archive:
                for e in nb.entries:
                    if e.get("consolidated"):
                        e["status"] = "archived"
                for e in nb.entries:
                    if e.get("type") == "semantic" and e.get("status") == "pending":
                        e["status"] = "confirmed"
            live = [e for e in nb.entries if e["status"] not in ("deleted", "archived")]
            dup = Counter(e["text"] for e in live)
            repeats = sum(v - 1 for v in dup.values() if v > 1)
            hit = sum(1 for t in facts if retrieval.retrieve(nb, t[:8], k=3))
            return dict(entries=len(live), repeats=repeats, hit=hit, applied=applied)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    return dict(archive=run(True), no_archive=run(False))


# E8 -----------------------------------------------------------------
TIME_WORDS = re.compile(r"(隔了|过了|隔)[^，。；]*?(秒|分钟|小时)[^，。；]*?[，。；]?")
RATER = """下面是一段聊天里“她”的回复（只有形式，没有内容）。判断她当时的身体状态更像哪一种：
good（还行）/ mild（有点累）/ bad（很差）。只输出一个词。"""


def three_c_redesign():
    """E8b：只用回复长度/标点（不含内容、不含秒数）判断状态。"""
    from . import api_client
    base = "evidence/p3/three_condition"
    key = {i["idx"]: i for i in json.load(open(base + "/key.json", encoding="utf-8-sig"))["A"]}
    text = open(base + "/A_full.txt", encoding="utf-8").read()
    parts = re.split(r"第\s*(\d+)\s*段", text)
    bars = {}
    for i in range(1, len(parts), 2):
        idx = int(parts[i])
        lines = [l.strip() for l in parts[i + 1].splitlines() if l.strip()]
        hers = [l for l in lines if l.startswith("她")]
        if not hers:
            continue
        avg = sum(len(x) for x in hers) / len(hers)
        bars[idx] = "…" * max(1, int(round(avg / 3))) + "。"
    prompt = ("下面只有她回复的“长度与标点”（不含内容、不含时间）。"
              "判断她当时的身体状态更像：good / mild / bad。只输出一个词。")
    rows = []
    for idx, bar in bars.items():
        scores = []
        for _ in range(3):
            try:
                raw = api_client.chat(prompt, bar, max_tokens=800, temperature=0.7)
            except Exception:
                raw = ""
            w = raw.strip().lower()
            scores.append(2 if "good" in w else (1 if "mild" in w else (0 if "bad" in w else 1)))
        rows.append((idx, float(np.mean(scores))))
    from scipy import stats
    xs = [s for _, s in rows if _ in key]
    ys = [key[i]["D"] for i, _ in rows if i in key]
    rho = stats.spearmanr(xs, -np.array(ys)).statistic if len(set(xs)) > 1 else float("nan")
    return dict(n=len(xs), rho=float(rho), rows=rows, bars=bars)


def main():
    out = {}
    for name, fn in (("u_identifiability", u_identifiability),
                     ("ablation_semantics", ablation_semantics),
                     ("consolidation_archive", consolidation_archive),
                     ("three_c_redesign", three_c_redesign)):
        try:
            out[name] = fn()
        except Exception as e:
            out[name] = dict(error=str(e))
    json.dump(out, open("evidence/p3/extra_experiments2.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
