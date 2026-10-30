# -*- coding: utf-8 -*-
"""Stub 测试床：把嘴固定成模板，整个系统变成确定性状态机。

用途：消融实验的可复现基线——同一 seed、同一事件流，输出哈希一致。
嘴不参与决策，只把状态/意图渲染成固定句式。
"""
import hashlib
import json

from . import params as P
from .model import Body
from .sim import Sim

TEMPLATES = {
    "ok": "嗯，还行。",
    "tired": "有点累。",
    "hungry": "饿了。",
    "lonely": "有点想说话。",
    "sick": "不太舒服。",
}


def _state_key(b: Body) -> str:
    if b.i > 0.5:
        return "sick"
    if b.e < 0.3:
        return "tired"
    if b.load < 0.3:
        return "hungry"
    if b.l > 0.6:
        return "lonely"
    return "ok"


def run(seed: int = 7, days: int = 30, product: bool = True) -> dict:
    sim = Sim(seed, (), seed, "allostatic", days, product=product)
    sim.run()
    trace = []
    for d in sim.daily:
        trace.append(dict(day=d.get("day"), sick=d.get("sick", 0),
                          meals=d.get("meals", 0), socials=d.get("socials", 0)))
    b = sim.body
    out = dict(seed=seed, days=days, t=sim.t,
               state=_state_key(b),
               reply=TEMPLATES[_state_key(b)],
               stats=dict(sick=sim.stats["sick"], meals=sim.stats["meals"],
                          socials=sim.stats["socials"], threats=sim.stats["threats"]),
               trace=trace)
    out["hash"] = hashlib.sha256(
        json.dumps(out, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    return out


if __name__ == "__main__":
    a = run(7, 30)
    b = run(7, 30)
    print(json.dumps(dict(hash=a["hash"], same=(a["hash"] == b["hash"]),
                          state=a["state"], reply=a["reply"]), ensure_ascii=False))
