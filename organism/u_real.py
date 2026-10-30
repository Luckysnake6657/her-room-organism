# -*- coding: utf-8 -*-
"""用真实发送记录估 U：离开越久，回来第一条是不是越短/越冷。

数据：evidence/p3/cmw_sessions/her_lines.jsonl（t=毫秒，key=会话）
方法：按时间排序；间隔 ≥18h 算一次"回来"；看回来第一条的长度
      与随后几条中位长度的比值，按间隔分桶。
这不是精确 U，只是行为侧的弱证据。
"""
import json
import statistics as st

PATH = "evidence/p3/cmw_sessions/her_lines.jsonl"
GAP = 18 * 3600 * 1000


def load():
    rows = []
    for line in open(PATH, encoding="utf-8"):
        d = json.loads(line)
        if d.get("key") == "private:owner" and d.get("t"):
            rows.append((float(d["t"]), str(d.get("text") or "")))
    rows.sort()
    return rows


def main():
    rows = load()
    groups = []
    for i in range(1, len(rows)):
        gap = rows[i][0] - rows[i - 1][0]
        if gap >= GAP:
            first = rows[i][1]
            after = [rows[j][1] for j in range(i + 1, min(i + 6, len(rows)))]
            if not after:
                continue
            base = st.median(len(t) for t in after)
            groups.append((gap / 86400000.0, len(first), base,
                           len(first) / base if base else 1.0))

    buckets = [(0.75, 1.5), (1.5, 3), (3, 7), (7, 999)]
    print("间隔(天) | n | 回来首条中位 | 之后中位 | 比值")
    for lo, hi in buckets:
        b = [g for g in groups if lo <= g[0] < hi]
        if not b:
            print("%.2f-%.2f | 0" % (lo, hi))
            continue
        print("%.2f-%.2f | %d | %.1f | %.1f | %.2f" % (
            lo, hi, len(b),
            st.median(x[1] for x in b), st.median(x[2] for x in b),
            st.median(x[3] for x in b)))
    if groups:
        print("总回来次数", len(groups))
        import math
        xs = [g[0] for g in groups]
        ys = [math.log(max(0.2, min(2.0, g[3]))) for g in groups]
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        den = sum((x - mx) ** 2 for x in xs) ** 0.5 * sum((y - my) ** 2 for y in ys) ** 0.5
        print("间隔 vs ln(比值) 相关", round(num / den, 3) if den else None)


if __name__ == "__main__":
    main()
