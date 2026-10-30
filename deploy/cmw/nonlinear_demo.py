# -*- coding: utf-8 -*-
"""验证成长机制是不是非线性的：阶跃、饱和、指数。"""
import os
import tempfile

from organism import consolidate, forget, model, notebook, params as P


def step_demo():
    """同一件事重复 N 次：1/2 次不巩固，第 3 次才跨过阈值。"""
    out = []
    for n in (1, 2, 3, 4):
        fd, p = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        open(p, "w", encoding="utf-8").write('{"next":1,"entries":[]}')
        nb = notebook.Notebook(p)
        for _ in range(n):
            nb.add("我下周三复查", type="fact")
        cands = consolidate.candidates(nb)
        out.append((n, len(cands)))
        os.remove(p)
    return out


def u_demo():
    """U 向 0.75 饱和：越接近越慢。"""
    out = []
    b = model.Body()
    for day in (1, 3, 7, 14, 28):
        b2 = model.Body()
        for _ in range(day * 24 * 60):
            b2.step(1, dict(hour=12.0, asleep=False, active=False, cold=0.0,
                            light=1.0, place=P.HOME))
        out.append((day, round(b2.u, 3)))
    return out


def forget_demo():
    """遗忘是指数：45 天半衰。"""
    import datetime as dt
    now = dt.datetime(2026, 10, 28)
    e = dict(created_at=(now - dt.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
             last_access=(now - dt.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
             strength=1.0, importance=0.5)
    return [(d, round(0.5 ** (d / 45.0), 3)) for d in (1, 7, 30, 45, 90)]


print("巩固阶跃（重复次数, 候选数）:", step_demo())
print("U 饱和（天, U）:", u_demo())
print("遗忘指数（天, 强度）:", forget_demo())
