# -*- coding: utf-8 -*-
"""只重生成行为文本（不动 runs.jsonl）。

渲染器改了措辞/粒度之后用这个，避免重写实验数据。
"""
import argparse
import os

from . import params as P
from .render import check_no_numbers, render_run
from .run_p0 import BASE_CONDITIONS
from .sim import Sim


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="evidence/p0")
    ap.add_argument("--seeds", default="0-2")
    ap.add_argument("--days", type=int, default=3)
    args = ap.parse_args(argv)

    seeds = []
    for part in args.seeds.split(","):
        if "-" in part:
            a, b = part.split("-")
            seeds.extend(range(int(a), int(b) + 1))
        else:
            seeds.append(int(part))

    tdir = os.path.join(args.out, "transcripts")
    os.makedirs(tdir, exist_ok=True)
    bad = 0
    n = 0
    for suffix, challenge in (("", False), ("_c", "std")):
        for name, lesion, mode, noise in BASE_CONDITIONS:
            for seed in seeds:
                res = Sim(seed, lesion, noise + seed, mode, P.DAYS,
                          challenge=challenge).run()
                text = render_run(res, seed, args.days)
                hits = check_no_numbers(text)
                bad += 1 if hits else 0
                with open(os.path.join(tdir, "%s_s%02d.txt" % (name + suffix, seed)),
                          "w", encoding="utf-8") as f:
                    f.write(text + "\n")
                n += 1
    print("rewrote %d transcripts (violations %d)" % (n, bad))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
