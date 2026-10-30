# -*- coding: utf-8 -*-
"""置信度校准：让"我有多确定"对得上"我有多准"。

依据 docs/memory-confidence-gate.md：
- 校准单位是**用户**，不是轨迹；每条"确认/纠正"是最贵的校准点；
- 用**块均值**（不是块最大，后者小样本会过度覆盖）；
- 报三件套：覆盖率、区间宽度、WIS——只报覆盖率是刷分。

v0 做的是"分箱均值"这一种最小 conformal：
把原始 confidence 映射到经验准确率，再报上面三件套。
不是完整 conformal prediction，别把它当保证。
"""
import math


def bin_means(pairs, bins: int = 5):
    """pairs: [(confidence, correct)] -> [(c_mean, y_mean, n)]，按 c 排序等分。"""
    if not pairs:
        return []
    s = sorted(pairs, key=lambda p: p[0])
    n = len(s)
    k = max(1, min(bins, n))
    out = []
    for i in range(k):
        lo = i * n // k
        hi = (i + 1) * n // k
        chunk = s[lo:hi]
        if not chunk:
            continue
        out.append((sum(c for c, _ in chunk) / len(chunk),
                    sum(y for _, y in chunk) / len(chunk), len(chunk)))
    return out


def _interp(c: float, table) -> float:
    if not table:
        return c
    if c <= table[0][0]:
        return table[0][1]
    if c >= table[-1][0]:
        return table[-1][1]
    for (c0, y0, _), (c1, y1, _) in zip(table, table[1:]):
        if c0 <= c <= c1:
            t = (c - c0) / (c1 - c0) if c1 > c0 else 0.0
            return y0 + t * (y1 - y0)
    return table[-1][1]


def calibrate(c: float, table) -> float:
    return max(0.0, min(1.0, _interp(c, table)))


def ece(pairs, table=None) -> float:
    """期望校准误差：分箱内 |平均置信 − 实际准确率| 的加权和。"""
    if not pairs:
        return 0.0
    s = sorted(pairs, key=lambda p: (calibrate(p[0], table) if table else p[0]))
    n, k = len(s), min(5, len(s))
    total = 0.0
    for i in range(k):
        chunk = s[i * n // k:(i + 1) * n // k]
        if not chunk:
            continue
        cs = [calibrate(c, table) if table else c for c, _ in chunk]
        ys = [y for _, y in chunk]
        total += abs(sum(cs) / len(cs) - sum(ys) / len(ys)) * len(chunk) / n
    return total


def coverage(pairs, table, theta: float = 0.70) -> float:
    """校准后 ≥θ 的那些，实际对的占多少。目标 ≥ θ。"""
    sel = [y for c, y in pairs if calibrate(c, table) >= theta]
    return sum(sel) / len(sel) if sel else float("nan")


def width(table) -> float:
    """区间宽度：每个箱覆盖的置信区间平均有多宽（越小越锐）。"""
    if not table:
        return 0.0
    return sum(abs(c1 - c0) for (c0, _, _), (c1, _, _) in zip(table, table[1:])) / max(1, len(table) - 1)


def wis(pairs, table, lam: float = 0.5) -> float:
    """本项目的 WIS 变体：Brier（校准后）+ λ·宽度。名字写清是变体。"""
    brier = sum((calibrate(c, table) - y) ** 2 for c, y in pairs) / max(1, len(pairs))
    return brier + lam * width(table)


def aci(theta: float, missed: bool, gamma: float = 0.02) -> float:
    """在线调阈值：漏了就降一点，没漏就升一点（γ 小防抖）。"""
    return min(0.95, max(0.40, theta + (gamma if not missed else -gamma)))
