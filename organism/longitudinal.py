# -*- coding: utf-8 -*-
"""30 天纵向：两种相处史，看第 1 天和第 30 天差在哪。

不调 API（dry），只看状态/态度/性格这条链，不看文采。
跑法：python -m organism.longitudinal
"""
import argparse
import json
import os

from . import attachment, drift, form, persona
from .chat import Session

WARM = ["你今天累不累", "谢谢", "我明天见", "你今天还好吗", "我回来了"]
COLD = ["随便", "无所谓", "别烦", "懒得", "不想聊"]


def run(arm: str, days: int = 30, seed: int = 7):
    s = Session(None, dry=True, persona=persona.PERSONA_V1, seed=seed)
    lines = WARM if arm == "warm" else COLD
    series = []
    for d in range(days):
        s.say(lines[d % len(lines)])
        s.sim.run(stop=s.sim.t + 1440)
        f = form.form_of(s.sim.body, persona=persona.PERSONA_V1)
        series.append(dict(day=d + 1,
                           regard=round(s.sim.body.regard, 3),
                           drift=round(s.sim.body.trait_drift, 3),
                           words=round(f["words"], 1),
                           willing=attachment.willing(s.sim.body, float(s.sim.body.s))))
    return series


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--out", default="evidence/p3/longitudinal.json")
    args = ap.parse_args(argv)

    warm = run("warm", args.days)
    cold = run("cold", args.days)
    for name, s in (("warm", warm), ("cold", cold)):
        last = s[-1]
        mid = s[len(s) // 2]
        tail_willing = sum(1 for x in s[-30:] if x["willing"]) / min(30, len(s))
        print("%-4s day1 r=%.2f d=%.3f w=%s | day%d r=%.2f d=%.3f w=%s | day%d r=%.2f d=%.3f w=%s | willing(尾部30天)=%.2f" % (
            name, s[0]["regard"], s[0]["drift"], s[0]["words"],
            mid["day"], mid["regard"], mid["drift"], mid["words"],
            last["day"], last["regard"], last["drift"], last["words"],
            tail_willing))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(dict(warm=warm, cold=cold), f, ensure_ascii=False, indent=2)
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
