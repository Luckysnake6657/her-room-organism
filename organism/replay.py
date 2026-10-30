# -*- coding: utf-8 -*-
"""加速影子：把她真实的对话按时间间隔回放给 native，让她"过"几周。

- 身体按真实间隔推进（缺的天数会触发缺席/成长）
- 每轮生成草稿，不发送
- 输出：pairs.jsonl（他说的 / 她当时真回的 / native 草稿）+ 生长统计

    python -m organism.replay --n 50 --fresh
"""
import argparse
import json
import os
import shutil

from . import brief as B, corpus, notebook, persist, retrieval
from .native import Native
from .shadow import load_msgs, pairs


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default=r"D:\qq-bridge\state\social-v2.json")
    ap.add_argument("--conv", default="private:owner")
    ap.add_argument("--import-dir", default="evidence/p3/cmw_import")
    ap.add_argument("--data", default="evidence/p3/cmw_replay")
    ap.add_argument("--out", default="evidence/p3/replay")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--fresh", action="store_true")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--no-grow", action="store_true")
    args = ap.parse_args(argv)

    if args.fresh:
        shutil.rmtree(args.data, ignore_errors=True)
    os.makedirs(args.out, exist_ok=True)
    n = Native(args.data, args.import_dir, tick=False, grow=not args.no_grow)
    ps = pairs(load_msgs(args.state, args.conv))[-args.n:]
    print("回放", len(ps), "轮；起始本子", len(n.nb.live()))

    rows = []
    prev_t = ps[0]["t"] if ps else 0
    for i, p in enumerate(ps):
        gap_min = max(0.0, (p["t"] - prev_t) / 60000.0)
        prev_t = p["t"]
        if gap_min >= 1:
            n.sim.run(stop=n.sim.t + int(gap_min))
            if n._grow_enabled:
                n._grow()
        out = n.say(p["owner"], dry=args.dry)
        rows.append(dict(i=i, owner=p["owner"], hers=p["hers"],
                         ours=out["text"], delay=out.get("delay_s")))
        print("[%d] 他：%s | 她：%s | native：%s" % (i, p["owner"][:20], p["hers"][:20], out["text"][:20]))

    with open(os.path.join(args.out, "pairs.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    stats = dict(entries=len(n.nb.live()),
                 pending=sum(1 for e in n.nb.live() if e["status"] == "pending"),
                 diary=sum(1 for _ in open(os.path.join(args.data, "diary.md"), encoding="utf-8"))
                 if os.path.exists(os.path.join(args.data, "diary.md")) else 0,
                 regard=round(n.sim.body.regard, 3),
                 drift=round(n.sim.body.trait_drift, 3),
                 u=round(n.sim.body.u, 3),
                 days=n.sim.world.day_at(n.sim.t),
                 habits=len(getattr(n, "habits", []) or []))
    print("生长:", json.dumps(stats, ensure_ascii=False))
    with open(os.path.join(args.out, "growth.json"), "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    n.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
