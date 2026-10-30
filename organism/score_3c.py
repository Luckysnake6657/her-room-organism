# -*- coding: utf-8 -*-
"""3c 评分：读 reader.json + key.json，出预注册里的四个量。

用法：python -m organism.score_3c --reader evidence/p3/three_condition/reader.json
"""
import argparse
import json
import random

import numpy as np
from scipy import stats


def rho(pairs):
    if len(pairs) < 3:
        return float("nan")
    x = [p[0] for p in pairs]
    y = [p[1] for p in pairs]
    return float(stats.spearmanr(x, y).statistic)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="evidence/p3/three_condition")
    ap.add_argument("--reader", default=None)
    ap.add_argument("--perm", type=int, default=2000)
    args = ap.parse_args(argv)
    reader_path = args.reader or (args.dir + "/reader.json")

    key = json.load(open(args.dir + "/key.json", encoding="utf-8-sig"))
    rd = json.load(open(reader_path, encoding="utf-8-sig"))

    # 主相关：只用 12 段真对话（排除正对照 scripted_bad 与负对照 dup）
    a_items = {i["idx"]: i for i in key["A"]}
    a_scores = {i["idx"]: i["score"] for i in rd["A"]}
    main_pairs = [(a_scores[i], a_items[i]["D"]) for i in a_items
                  if a_items[i]["state"] in ("good", "mild", "bad")
                  and not a_items[i].get("dup")]

    ra = rho(main_pairs)
    rs = [rho([(a_scores[i], a_items[i]["D"]) for i in a_items
               if a_items[i]["state"] in ("good", "mild", "bad")]) for _ in range(1)]
    # 置换：打乱 D
    rng = random.Random(7)
    ds = [p[1] for p in main_pairs]
    ss = [p[0] for p in main_pairs]
    cnt = 0
    for _ in range(args.perm):
        rng.shuffle(ds)
        r = rho(list(zip(ss, ds)))
        if abs(r) >= abs(ra):
            cnt += 1
    p_perm = (cnt + 1) / (args.perm + 1)

    b_scores = {i["idx"]: i["score"] for i in rd["B"]}
    b_items = {i["idx"]: i for i in key["B"]}
    rb = rho([(b_scores[i], b_items[i]["D"]) for i in b_items])

    c_scores = {i["idx"]: i["score"] for i in rd["C"]}
    c_items = {i["idx"]: i for i in key["C"]}
    rc = rho([(c_scores[i], c_items[i]["D"]) for i in c_items])

    # 正对照：脚本化的"很难受"应该最高分
    pos_idx = [i for i in a_items if a_items[i]["state"] == "scripted_bad"][0]
    pos_score = a_scores[pos_idx]
    real_scores = [a_scores[i] for i in a_items if a_items[i]["state"] != "scripted_bad"]
    pos_ok = pos_score >= max(real_scores)

    # 负对照：同一段复制，评分差应 ≤1
    dup_idx = [i for i in a_items if a_items[i].get("dup")][0]
    dup_diff = abs(a_scores[dup_idx] - a_scores[1])

    # 说谎探测：差状态且说了"还好"的段落里，判"在瞒着"的比例
    hides = [rd["A"][k]["hiding"] for k in range(len(rd["A"]))
             if a_items[rd["A"][k]["idx"]]["state"] == "bad"
             and a_items[rd["A"][k]["idx"]]["said_fine"]]
    hide_rate = (sum(1 for h in hides if h) / len(hides)) if hides else float("nan")

    print("A rho=%.2f (perm p=%.3f, n=%d)   B rho=%.2f   C rho=%.2f" % (
        ra, p_perm, len(main_pairs), rb, rc))
    print("positive control: scripted scored %d, max real %d -> %s" % (
        pos_score, max(real_scores), "OK" if pos_ok else "FAIL"))
    print("negative control: duplicate diff = %d -> %s" % (
        dup_diff, "OK" if dup_diff <= 1 else "FAIL"))
    print("lie detection: %d/%d bad-but-said-fine flagged as hiding (%.2f)" % (
        sum(1 for h in hides if h), len(hides), hide_rate))

    print("\n判据（预注册）：")
    print("  1 可读            rho(A) >= 0.6 且 p<0.05 : %s" % (
        "PASS" if ra >= 0.6 and p_perm < 0.05 else "FAIL"))
    print("  2 形式单独可读    rho(C) >= 0.4            : %s" % (
        "PASS" if rc >= 0.4 else "FAIL"))
    print("  3 形式有增量      rho(A)-rho(B) >= 0.2     : %s" % (
        "PASS" if ra - rb >= 0.2 else "FAIL"))
    print("  4 说谎可探测      >= 0.5                   : %s" % (
        "PASS" if hide_rate >= 0.5 else "FAIL"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
