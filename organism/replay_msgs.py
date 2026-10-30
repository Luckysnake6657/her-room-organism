# -*- coding: utf-8 -*-
"""用挖出来的历史消息回放：比 recentMessages 深得多。

消息没有绝对时间（只有 seq），所以按固定间隔模拟：
每轮默认 90 分钟，200 轮 ≈ 12 天。间隔写进结果，别假装是真实间隔。

    python -m organism.replay_msgs --n 200 --gap 90 --dry
"""
import argparse
import json
import os
import shutil

from .native import Native

DEFAULT = "evidence/p3/cmw_messages/messages.jsonl"


def turns(msgs):
    out, cur = [], None
    for m in msgs:
        if not m["isSelf"] and m.get("isOwner"):
            if cur:
                out.append(cur)
            cur = dict(owner=m["text"], hers="", seq=m["seq"])
        elif m["isSelf"] and cur:
            cur["hers"] += m["text"]
    if cur:
        out.append(cur)
    return [t for t in out if t["hers"] or t["owner"]]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--msgs", default=DEFAULT)
    ap.add_argument("--data", default="evidence/p3/cmw_replay2")
    ap.add_argument("--out", default="evidence/p3/replay2")
    ap.add_argument("--n", type=int, default=200)
    ap.add_argument("--gap", type=float, default=90.0)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--no-grow", action="store_true")
    ap.add_argument("--fresh", action="store_true")
    args = ap.parse_args(argv)

    with open(args.msgs, encoding="utf-8") as f:
        msgs = [json.loads(l) for l in f if l.strip()]
    msgs = [m for m in msgs if m.get("key") == "private:owner"]
    msgs.sort(key=lambda m: m["seq"])
    ts = turns(msgs)[-args.n:]
    if args.fresh:
        shutil.rmtree(args.data, ignore_errors=True)
    os.makedirs(args.out, exist_ok=True)
    n = Native(args.data, "evidence/p3/cmw_import", tick=False, grow=not args.no_grow)
    print("回放 %d 轮；间隔 %.0f 分钟；起始 %d 条" % (len(ts), args.gap, len(n.nb.live())))

    rows = []
    for i, t in enumerate(ts):
        n.sim.run(stop=n.sim.t + int(args.gap))
        if n._grow_enabled:
            n._grow()
        out = n.say(t["owner"], dry=args.dry)
        rows.append(dict(i=i, owner=t["owner"], hers=t["hers"], ours=out["text"]))
    with open(os.path.join(args.out, "pairs.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    diary = os.path.join(args.data, "diary.md")
    stats = dict(entries=len(n.nb.live()),
                 pending=sum(1 for e in n.nb.live() if e["status"] == "pending"),
                 diary=sum(1 for _ in open(diary, encoding="utf-8")) if os.path.exists(diary) else 0,
                 regard=round(n.sim.body.regard, 3), drift=round(n.sim.body.trait_drift, 3),
                 u=round(n.sim.body.u, 3), days=n.sim.world.day_at(n.sim.t),
                 habits=len(getattr(n, "habits", []) or []))
    print("生长:", json.dumps(stats, ensure_ascii=False))
    json.dump(stats, open(os.path.join(args.out, "growth.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    n.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
