# -*- coding: utf-8 -*-
"""设计输入回放：不是等真实消息，而是喂能触发阶跃的输入，看曲线走不走。

剧本（12 天）：
- 第 1–3 天：同一件事每天说一次 → 第 3 天应该巩固
- 第 1–3 天：同一行为每天一次 → 第 3 天应该成习惯
- 第 1–5、11–12 天：每天正面互动 → regard 递减上升
- 第 6–10 天：完全失联 → U 上升；回来后再降
"""
import argparse
import json
import os
import shutil

from . import consolidate, relation
from .native import Native


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="evidence/p3/cmw_story")
    ap.add_argument("--out", default="evidence/p3/story")
    ap.add_argument("--clean", action="store_true", help="用空本子，才能看到阶跃")
    args = ap.parse_args(argv)
    shutil.rmtree(args.data, ignore_errors=True)
    os.makedirs(args.out, exist_ok=True)
    imp = "evidence/p3/cmw_import"
    if args.clean:
        imp = os.path.join(args.data, "_imp")
        os.makedirs(imp, exist_ok=True)
        shutil.copy(os.path.join("evidence/p3/cmw_import", "persona.json"),
                    os.path.join(imp, "persona.json"))
        with open(os.path.join(imp, "notebook.json"), "w", encoding="utf-8") as f:
            f.write('{"next": 1, "entries": []}')
    n = Native(args.data, imp, tick=False, grow=True)

    rows = []
    for day in range(1, 13):
        contact = day <= 5 or day >= 11
        if day <= 3:
            for t, ty in (("我下周三复查", "fact"), ("今天去复查了", "event")):
                e = n.nb.add(t, type=ty, status="confirmed", confidence=0.9)
                e["created_at"] = n.sim_now().strftime("%Y-%m-%dT%H:%M:%S")
        if contact:
            n.sim.body.tend()
            relation.update(n.sim.body, "你怎么样，记得吃饭")
        n.sim.run(stop=n.sim.t + 24 * 60)
        cand = len(consolidate.candidates(n.nb))
        n._grow()
        diary = os.path.join(args.data, "diary.md")
        rows.append(dict(
            day=day, contact=contact, cand=cand,
            habits=len(getattr(n, "habits", []) or []),
            regard=round(n.sim.body.regard, 4), u=round(n.sim.body.u, 3),
            diary=sum(1 for _ in open(diary, encoding="utf-8")) if os.path.exists(diary) else 0,
            entries=len(n.nb.live()),
            pending=sum(1 for e in n.nb.live() if e["status"] == "pending")))

    for r in rows:
        print("D%02d 联系=%s 巩固=%d 习惯=%d regard=%.3f U=%.3f 日记=%d 条目=%d pending=%d" % (
            r["day"], "是" if r["contact"] else "否", r["cand"], r["habits"],
            r["regard"], r["u"], r["diary"], r["entries"], r["pending"]))
    json.dump(rows, open(os.path.join(args.out, "story.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    n.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
