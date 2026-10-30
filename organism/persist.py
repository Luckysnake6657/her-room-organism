# -*- coding: utf-8 -*-
"""离线续算：把机体落盘，隔一段时间再打开，按流逝的时间补算。

判据（P1）：
    连续跑 7 天  ==  跑 3 天 + 落盘 + 离线 4 天 + 读档 + 补算 4 天
"==" 指六系统状态、内钟、位置、食物、RNG 位置逐位相同。

为什么能逐位相同：
- 世界的外生随机数由 seed 决定（预生成），存档只需要记住 seed 和 t；
- 政策噪声 RNG 的 bit_generator 状态一起存；
- 存档时若正在做一件事（走路/睡觉），把这件事和剩余时间一起存。

注意：这只保证"补算和连续跑一致"，**不回答**"补算的那几天算不算真的发生过"——
那是产品问题（HANDOFF §五 的悬置问题 2），不是实现问题。
"""
import json
import time

from . import params as P
from .model import Body
from .sim import Sim

VERSION = 1


def dump(sim: Sim) -> dict:
    b = sim.body
    return dict(
        version=VERSION,
        seed=sim.seed,
        lesion=list(sim.lesion),
        edges_off=list(sim.edges_off),
        mode=sim.mode,
        challenge=json.loads(json.dumps(sim.challenge)),
        days=sim.days,
        t=sim.t,
        saved_at=time.time(),
        started=bool(getattr(sim, "_started", False)),
        action=sim.action,
        body=dict(e=b.e, s=b.s, a=b.a, i=b.i, l=b.l, phi=b.phi,
                  load=b.load, infect=b.infect, oor=dict(b.oor),
                  dead=b.dead, death_cause=b.death_cause, death_t=b.death_t,
                  chronic=dict(b.chronic), losses=dict(b.losses),
                  u=b.u, contact_today=b._contact_today,
                  regard=b.regard, regard_log=list(b.regard_log),
                  regard_week=b.regard_week,
                  trait_drift=b.trait_drift, trait_log=list(b.trait_log),
                  working=list(b.working),
                  hour=getattr(b, "_hour", P.T_START_MIN / 60.0)),
        world=dict(place=sim.world.place, food=sim.world.food),
        rng=sim.rng.bit_generator.state,
        stats=sim.stats,
        daily=sim.daily,
        events=sim.events,
        d_sum=sim._d_sum, d_n=sim._d_n, l_max=getattr(sim, "_l_max", 0.0),
    )


def save(sim: Sim, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(dump(sim), f, ensure_ascii=False)


def load(path: str) -> Sim:
    with open(path, encoding="utf-8") as f:
        st = json.load(f)
    assert st["version"] == VERSION, "存档版本不对: %s" % st["version"]

    sim = Sim(st["seed"], tuple(st["lesion"]), 0, st["mode"], st["days"],
              challenge=st["challenge"], edges_off=tuple(st["edges_off"]))
    b = sim.body
    for k, v in st["body"].items():
        if k == "oor":
            b.oor.update(v)
        elif k == "hour":
            b._hour = v
        elif k == "contact_today":
            b._contact_today = v
        else:
            setattr(b, k, v)
    sim.world.place = st["world"]["place"]
    sim.world.food = st["world"]["food"]
    sim.t = st["t"]
    sim.action = st["action"]
    sim._started = st["started"]
    sim.rng.bit_generator.state = st["rng"]
    sim.stats = st["stats"]
    sim.daily = st["daily"]
    sim.events = st["events"]
    sim._d_sum = st["d_sum"]
    sim._d_n = st["d_n"]
    sim._l_max = st["l_max"]
    sim.saved_at = st.get("saved_at", time.time())
    return sim


def advance_offline(sim: Sim, real_minutes: float = None, scale: float = None) -> Sim:
    """离线过去了多少真实分钟，就补算对应的模拟时间。

    real_minutes=None 时按存档时间戳算（真正的"关掉再打开"）。
    """
    scale = P.SIM_MIN_PER_REAL_MIN if scale is None else scale
    if real_minutes is None:
        real_minutes = max(0.0, (time.time() - getattr(sim, "saved_at", time.time())) / 60.0)
    target = sim.t + int(round(real_minutes * scale))
    sim.run(stop=target)
    return sim


def resume(sim: Sim, real_minutes: float = None, scale: float = None) -> Sim:
    """补算并留一份"这段时间发生了什么"的结算单（世界账，不是情感账）。"""
    before = dict(t=sim.t, D=sim.body.D(),
                  meals=sim.stats["meals"], socials=sim.stats["socials"],
                  threats=sim.stats["threats"], sick=sim.stats["sick"],
                  asleep=sim.stats["asleep"], minutes=sim.stats["minutes"],
                  missed=sim.stats.get("missed_windows", 0),
                  losses=dict(sim.body.losses))
    advance_offline(sim, real_minutes, scale)
    # 只留世界侧的事实。"她的状态从多少变到多少"不进结算单——
    # 关系界面会把它自动翻译成"她不好，而你不在"（见 docs/cost-and-guilt.md）。
    sim.last_gap = dict(
        sim_minutes=sim.t - before["t"],
        days_alone=round((sim.t - before["t"]) / 1440.0, 2),
        meals=sim.stats["meals"] - before["meals"],
        socials=sim.stats["socials"] - before["socials"],
        threats=sim.stats["threats"] - before["threats"],
        sick_minutes=sim.stats["sick"] - before["sick"],
        asleep_minutes=sim.stats["asleep"] - before["asleep"],
        missed_windows=sim.stats.get("missed_windows", 0) - before["missed"],
    )
    return sim
