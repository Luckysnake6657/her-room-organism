# -*- coding: utf-8 -*-
"""真实世界看门狗：轮询"你在不在"，把离开/回来喂给会话。

跑法：python -m organism.watch --every 30
（真产品里这就是托盘进程；这里是命令行版，方便测。）
"""
import argparse
import time

from . import realtime
from .chat import Session


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", default="evidence/p3/watch_session.json")
    ap.add_argument("--every", type=int, default=30)
    ap.add_argument("--idle-max", type=float, default=300.0,
                    help="超过这么多秒没输入就算离开")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--once", action="store_true", help="只查一次，用于自检")
    args = ap.parse_args(argv)

    s = Session(args.session, dry=args.dry)
    print("在场阈值 %.0f 秒；每 %d 秒查一次" % (args.idle_max, args.every))
    while True:
        snap = realtime.snapshot(args.idle_max)
        ev = s.on_presence(snap["present"])
        if ev["event"] in ("away", "back"):
            print("[%s] %s %s" % (snap["at"], ev["event"],
                                  ("离开 %.0f 分钟" % (ev["away_s"] / 60.0))
                                  if ev["event"] == "back" else ""))
        if args.once:
            print(ev)
            return 0
        time.sleep(args.every)


if __name__ == "__main__":
    raise SystemExit(main())
