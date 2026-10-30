# -*- coding: utf-8 -*-
"""U 半衰期的敏感性模拟：不同 τ 下，离开 1/3/7/14/30 天，她冷到什么程度。

U = U_MAX * (1 - 2^(-gap/τ))
延迟倍率 = 1 + 0.8U；字数倍率 = 1 - 0.5U（和 form.py 一致）

注意：这是设计模拟，不是用真实数据定标。
"""
from . import params as P


def u_of(gap, tau):
    return P.U_MAX * (1.0 - 0.5 ** (gap / tau))


def main():
    print("τ(天) | 1d U/延迟/字数 | 3d | 7d | 14d | 30d")
    for tau in (3, 7, 14, 28, 56):
        cells = []
        for g in (1, 3, 7, 14, 30):
            u = u_of(g, tau)
            cells.append("%.2f/×%.2f/×%.2f" % (u, 1 + 0.8 * u, 1 - 0.5 * u))
        print("%5d | %s" % (tau, " | ".join(cells)))


if __name__ == "__main__":
    main()
