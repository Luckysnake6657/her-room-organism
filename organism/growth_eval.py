# -*- coding: utf-8 -*-
"""成长是不是非线性的：阶跃/饱和/递减/指数。

不是数日记，是看状态跃迁。判据先写死：
- 巩固：第 3 次重复才出现候选（0,0,1）
- 习惯：14 天内第 3 次才成习惯（0,0,≥1）
- regard：连续正面互动，增量递减（第一步 > 最后一步）
- U：28 天不上线，饱和（凹、<上限）
- 遗忘：45 天强度减半
"""
import datetime as dt
import os
import tempfile

from . import consolidate, forget, habits, model, notebook, params as P, relation


def _fresh():
    fd, p = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    with open(p, "w", encoding="utf-8") as f:
        f.write('{"next": 1, "entries": []}')
    return notebook.Notebook(p), p


def consolidation_step():
    out = []
    for n in (1, 2, 3):
        nb, p = _fresh()
        try:
            base = dt.datetime(2026, 10, 28)
            for i in range(n):
                e = nb.add("我下周三复查", type="fact")
                e["created_at"] = (base - dt.timedelta(days=n - 1 - i)).strftime(
                    "%Y-%m-%dT%H:%M:%S")
            out.append(len(consolidate.candidates(nb, now=base)))
        finally:
            os.remove(p)
    return out


def habit_step():
    out = []
    for n in (1, 2, 3):
        nb, p = _fresh()
        try:
            for _ in range(n):
                nb.add("今天去复查了", type="event")
            out.append(len(habits.detect(nb)))
        finally:
            os.remove(p)
    return out


def regard_curve(steps=30):
    b = model.Body()
    vals = []
    for _ in range(steps):
        relation.update(b, "你怎么样，记得吃饭")
        vals.append(round(b.regard, 4))
    return vals


def u_curve():
    out = []
    for day in (1, 3, 7, 14, 28):
        b = model.Body()
        for _ in range(day * 24 * 60):
            b.step(1, dict(hour=12.0, asleep=False, active=False, cold=0.0,
                           light=1.0, place=P.HOME))
        out.append(round(b.u, 3))
    return out


def forgetting_curve():
    now = dt.datetime(2026, 10, 28)
    e = dict(created_at=(now - dt.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
             last_access=(now - dt.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
             strength=1.0, importance=0.5)
    return [(d, round(0.5 ** (d / 45.0), 3)) for d in (1, 7, 45)]


def run():
    c = consolidation_step()
    h = habit_step()
    r = regard_curve()
    u = u_curve()
    checks = dict(
        consolidation_step=(c == [0, 0, 1]),
        habit_step=(h[:2] == [0, 0] and h[2] >= 1),
        regard_diminishing=((r[0] - 0.5) > (r[-1] - r[-2]) and r[-1] > 0.5),
        u_saturating=(u[0] < u[1] < u[2] < u[3] < u[4] < P.U_MAX
                      and ((u[1] - u[0]) / 2.0) > ((u[4] - u[3]) / 14.0)),
        forgetting_halves=(forgetting_curve()[2][1] <= 0.5),
    )
    return dict(ok=all(checks.values()), checks=checks,
                curves=dict(consolidation=c, habits=h, regard=r, u=u,
                            forgetting=forgetting_curve()))


if __name__ == "__main__":
    r = run()
    for k, v in r["checks"].items():
        print(("PASS " if v else "FAIL ") + k)
    print(r["curves"])
    raise SystemExit(0 if r["ok"] else 1)
