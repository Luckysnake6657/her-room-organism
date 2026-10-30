# -*- coding: utf-8 -*-
"""缺席：把"app 关掉"和"人离开键盘"合成同一个概念。

两条路原来各走各的：
- 关掉 → `persist.resume` 按挂钟补算，产出 `last_gap`
- 离开键盘 → `Session.on_presence` 按空闲推进

现在两者都产出同一种记录：`Absence`。结算只认它。
"""
from . import params as P


def _gap_from_stats(sim, before: dict, minutes: float) -> dict:
    return dict(
        days_alone=round(minutes / P.MIN_PER_DAY, 3),
        meals=sim.stats["meals"] - before["meals"],
        socials=sim.stats["socials"] - before["socials"],
        threats=sim.stats["threats"] - before["threats"],
        sick_minutes=sim.stats["sick"] - before["sick"],
        missed_windows=sim.stats.get("missed_windows", 0) - before["missed"],
    )


def make(kind: str, minutes: float, gap: dict) -> dict:
    """kind: 'closed'（app 关掉）或 'idle'（人离开键盘）。"""
    return dict(kind=kind, minutes=round(minutes, 1), gap=gap,
                long=minutes >= P.MIN_PER_DAY)


def from_gap(gap: dict, kind: str = "closed") -> dict:
    minutes = float(gap.get("days_alone", 0.0)) * P.MIN_PER_DAY
    return make(kind, minutes, gap)


def from_window(sim, before: dict, minutes: float) -> dict:
    return make("idle", minutes, _gap_from_stats(sim, before, minutes))


def stats_now(sim) -> dict:
    return dict(meals=sim.stats["meals"], socials=sim.stats["socials"],
                threats=sim.stats["threats"], sick=sim.stats["sick"],
                missed=sim.stats.get("missed_windows", 0))
