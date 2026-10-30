# -*- coding: utf-8 -*-
"""数据边界命令行。

    python -m organism.data --session evidence/p3/demo_meet.json --what
    python -m organism.data --session ... --notebook ... --export backup.json
    python -m organism.data --session ... --notebook ... --delete --yes
"""
import argparse

from . import privacy


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--session", default="evidence/p3/demo_meet.json")
    ap.add_argument("--notebook", default=None)
    ap.add_argument("--what", action="store_true", help="显示告知")
    ap.add_argument("--export", default=None)
    ap.add_argument("--delete", action="store_true")
    ap.add_argument("--yes", action="store_true", help="删除必须显式确认")
    args = ap.parse_args(argv)

    if args.what:
        print(privacy.disclosure())
        return 0

    if args.export:
        privacy.export(args.session, args.notebook, args.export)
        print("已导出到", args.export, "（不含 API key）")
        return 0

    if args.delete:
        if not args.yes:
            print("删除不可恢复；确认请加 --yes")
            return 1
        r = privacy.delete(args.session, args.notebook)
        print("删除结果：", r)
        return 0 if r["ok"] else 1

    print(privacy.disclosure())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
