# -*- coding: utf-8 -*-
"""P0 模拟循环：把身体、世界、政策接起来，产出行为记录与特征。"""
import math

import numpy as np

from . import params as P
from .model import Body, World
from .policy import Policy


class Sim:
    def __init__(self, seed: int, lesion=(), noise_seed: int = 0,
                 policy_mode: str = "allostatic", days: int = P.DAYS,
                 challenge=False, edges_off=(), debug_at=None, product=None):
        self.debug_at = debug_at
        self.seed = int(seed)
        self.lesion = tuple(sorted(lesion))
        self.edges_off = tuple(sorted(edges_off))
        self.noise_seed = int(noise_seed)
        self.mode = policy_mode
        self.challenge = challenge
        self.product = P.PRODUCT_MODE if product is None else bool(product)
        self.world = World(seed, days, challenge=challenge)
        self.body = Body(lesion, edges_off, product=self.product)
        self.rng = np.random.default_rng(noise_seed)
        self.policy = Policy(self.rng, mode=policy_mode)
        self.days = days
        self.t = self.world.start
        self.action = None
        self.events = []
        self.trace = []
        self._d_sum = 0.0
        self._d_n = 0
        self._x_sum = dict(e=0.0, s=0.0, a=0.0, i=0.0, l=0.0, m=0.0)
        self.daily = [self._blank_day(i) for i in range(days)]
        self.stats = dict(
            minutes=0, asleep=0, out=0, night_awake=0, sick=0,
            meals=0, socials=0, no_one=0, travels=0, flees=0,
            threats=0, infections=0, bouts=0, active=0,
            missed_windows=0,
            active_day=0, active_night=0,
            act=dict(eat=0, sleep=0, rest=0, social=0, goto=0),
            onsets=[],
        )

    @staticmethod
    def _blank_day(i):
        return dict(idx=i, meals=0, socials=0, out=0, asleep=0, threats=0,
                    sick=0, bouts=0, first_out=None, woke=None, slept=None)

    # ------------------------------------------------------------------
    def log(self, t: int, kind: str, **kw):
        d = self.world.day_at(t)
        while d >= len(self.daily):
            self.daily.append(self._blank_day(len(self.daily)))
        self.events.append(dict(day=d, hour=round(self.world.hour_at(t), 2),
                                kind=kind, t=t, **kw))
        day = self.daily[d]
        if kind == "meal":
            day["meals"] += 1
        elif kind == "social":
            day["socials"] += 1
        elif kind == "threat":
            day["threats"] += 1
        elif kind == "wake":
            day["woke"] = round(self.world.hour_at(t), 2)
        elif kind == "sleep":
            day["slept"] = round(self.world.hour_at(t), 2)

    # ------------------------------------------------------------------
    def _ctx(self, t: int):
        act = self.action
        asleep = bool(act and act.get("asleep"))
        active = bool(act and act.get("active"))
        traveling = bool(act and act["kind"] in ("goto", "flee"))
        hour = self.world.hour_at(t)
        origin = self.world.place
        dest = act.get("dest", origin) if act else origin
        if traveling:
            place = dest
            cold = 0.5 * (self.world.cold(origin, hour) + self.world.cold(dest, hour))
            light = P.LIGHT_OUT
        else:
            place = origin
            cold = self.world.cold(place, hour)
            light = self.world.light(place, asleep)
        return dict(hour=hour, asleep=asleep, active=active, cold=cold,
                    light=light, place=place, traveling=traveling)

    # ------------------------------------------------------------------
    def _choose(self, t: int):
        # 饿极了的硬反射：先吃，别的事以后再说
        if ("energy" not in self.body.lesion and self.body.e < 0.15
                and not (self.action and self.action.get("asleep"))):
            if self.world.place == P.FOOD and self.world.food_available():
                act = dict(kind="eat", dur=P.MEAL_MIN, dest=P.FOOD, active=True,
                           eat=True, start=t, end=t + P.MEAL_MIN)
            elif self.world.place != P.FOOD:
                hops = P.HOPS[self.world.place][P.FOOD]
                dur = hops * P.TRAVEL_MIN_PER_HOP
                act = dict(kind="goto", dur=dur, dest=P.FOOD, active=True,
                           start=t, end=t + dur)
            else:
                act = dict(kind="rest", dur=P.REST_MIN, dest=self.world.place,
                           start=t, end=t + P.REST_MIN)
            self.action = act
            return

        act = self.policy.choose(self.body, self.world, t)
        if getattr(self, "debug_at", None) is not None:
            lo, hi = self.debug_at
            if lo <= t <= hi:
                opts = self.policy.options(self.body, self.world, t)
                print("DEBUG t=%d hour=%.2f place=%d e=%.2f s=%.2f a=%.2f i=%.2f l=%.2f food=%.2f D=%.3f vals=%s" % (
                    t, self.world.hour_at(t), self.world.place, self.body.e, self.body.s,
                    self.body.a, self.body.i, self.body.l, self.world.food,
                    self.body.D(), {k: round(v, 2) for k, v in self.body.values().items()}))
                for o in sorted(opts, key=lambda x: -x["value"]):
                    print("   %-6s dur=%3d u=%+.3f dest=%s" % (
                        o["kind"], o["dur"], o["value"], o.get("dest")))
        act.setdefault("dest", self.world.place)
        if act["kind"] == "sleep":
            self.stats["bouts"] += 1
            self.stats["onsets"].append(round(self.world.hour_at(t), 2))
            self.daily[self.world.day_at(t)]["bouts"] += 1
            self.log(t, "sleep")
        self.action = act

    def _finish(self, t: int):
        act = self.action
        self.action = None
        if act is None:
            return
        kind = act["kind"]
        if kind == "eat":
            if self.world.place == P.FOOD and self.world.food_available():
                self.body.meal()
                self.world.food = max(0.0, self.world.food - P.MEAL_FOOD_COST)
                self.stats["meals"] += 1
                self.log(t, "meal")
            else:
                self.log(t, "no_food")
        elif kind == "social":
            if self.world.person_present(t):
                self.body.contact(npc=True)
                self.stats["socials"] += 1
                self.log(t, "social")
            else:
                self.stats["no_one"] += 1
                self.log(t, "no_one")
        elif kind in ("goto", "flee"):
            self.world.place = act["dest"]
            self.stats["travels"] += 1
            self.log(t, "arrive", place=act["dest"])
        elif kind == "sleep":
            self.log(t, "wake")

    def _interrupt_for_threat(self, t: int):
        """被吓到：醒了，往家跑。"""
        self.stats["flees"] += 1
        if self.action is not None:
            self.action = None
        if self.world.place != P.HOME:
            hops = P.HOPS[self.world.place][P.HOME]
            self.action = dict(kind="flee", dur=hops * P.TRAVEL_MIN_PER_HOP,
                               dest=P.HOME, active=True, start=t)
            self.action["end"] = t + self.action["dur"]
            self.log(t, "flee")
        else:
            self.action = dict(kind="rest", dur=20, dest=P.HOME, start=t, end=t + 20)

    # ------------------------------------------------------------------
    def run(self, stop=None):
        w, b = self.world, self.body
        t = self.t
        stop = w.end if stop is None else min(int(stop), w.end)
        if not getattr(self, "_started", False):
            self.log(t, "wake")
            self._started = True
        while t < stop and not b.dead:
            asleep = bool(self.action and self.action.get("asleep"))
            ctx = self._ctx(t)
            b.step(P.DT_MIN, ctx)
            events = w.advance(b, ctx["place"], asleep, P.DT_MIN, t)
            for ev in events:
                self.log(t, ev["kind"], place=ev.get("place"),
                         injury=ev.get("injury", False))
                if ev["kind"] == "threat":
                    self.stats["threats"] += 1
                    self._interrupt_for_threat(t)
                elif ev["kind"] == "infection":
                    self.stats["infections"] += 1
                elif ev["kind"] == "person_left":
                    # 窗口关了：今天有人来，但她一次都没去见
                    if self.daily[w.day_at(t)]["socials"] == 0:
                        self.stats["missed_windows"] += 1
                        b.record_loss("missed_windows", 1)
                        b.record_loss("days_alone", 1)

            # --- 分钟级统计 ---
            self.stats["minutes"] += 1
            hour = w.hour_at(t)
            night = w.is_night(hour)
            d_now = w.day_at(t)
            last_day = getattr(self, "_last_day", None)
            if last_day is None:
                self._last_day = d_now
            elif d_now != last_day:
                self._last_day = d_now
                self.body._contact_today = False
            day = self.daily[d_now]
            if asleep:
                self.stats["asleep"] += 1
                day["asleep"] += 1
            if w.place != P.HOME or (self.action and self.action["kind"] in ("flee", "goto")):
                self.stats["out"] += 1
                day["out"] += 1
                if day["first_out"] is None:
                    day["first_out"] = round(hour, 2)
            if night and not asleep:
                self.stats["night_awake"] += 1
            if b.i > P.I_SICK_THRESH:
                self.stats["sick"] += 1
                day["sick"] += 1
            if self.action is not None:
                k = self.action["kind"]
                if k in self.stats["act"]:
                    self.stats["act"][k] += 1
                if k in ("goto", "flee"):
                    self.stats["active"] += 1
                    if 8.0 <= hour < 20.0:
                        self.stats["active_day"] += 1
                    else:
                        self.stats["active_night"] += 1
            if self.stats["minutes"] % 10 == 0:
                self._d_sum += b.D()
                self._d_n += 1
                self._x_sum["e"] += b.e
                self._x_sum["s"] += b.s
                self._x_sum["a"] += b.a
                self._x_sum["i"] += b.i
                self._x_sum["l"] += b.l
                self._x_sum["m"] += b.values()["misalign"]
                self._l_max = max(getattr(self, "_l_max", 0.0), b.l)
            if self.stats["minutes"] % 60 == 0:
                self.trace.append(dict(
                    t=t, day=w.day_at(t), hour=round(hour, 2), place=w.place,
                    kind=(self.action["kind"] if self.action else "-"),
                    e=round(b.e, 3), s=round(b.s, 3), a=round(b.a, 3),
                    i=round(b.i, 3), l=round(b.l, 3), phi=round(b.phi, 2),
                    D=round(b.D(), 3)))

            t += 1
            self.t = t

            if b.dead:
                b.death_t = t
                break

            # --- 困到极限：不受控制地睡过去（饿着的时候睡不了） ---
            if (not self.body.dead and b.s > P.S_MICROSLEEP and b.e > 0.20
                    and not (self.action and self.action.get("asleep"))):
                self.action = dict(kind="sleep", dur=P.MICROSLEEP_MIN, dest=w.place,
                                   asleep=True, nap=False, forced=True,
                                   start=t, end=t + P.MICROSLEEP_MIN)
                self.stats["bouts"] += 1
                self.stats["onsets"].append(round(hour, 2))
                self.daily[w.day_at(t)]["bouts"] += 1
                self.log(t, "collapse")

            # --- 动作结束 ---
            if self.action is not None and t >= self.action["end"]:
                self._finish(t)

            # --- 睡眠的自动醒：晨间窗口 + 睡饱；白天补觉有上限 ---
            if self.action is not None and self.action["kind"] == "sleep":
                b = self.body
                morning = b.morning_signal()
                sleepy_gone = b.s <= P.S_WAKE_AT and morning >= P.WAKE_GATE
                nap_done = self.action.get("nap") and (t - self.action["start"]) >= P.NAP_MAX_MIN
                hunger_wake = (b.e <= P.S_HUNGER_WAKE
                               and (t - self.action["start"]) >= 20)
                if sleepy_gone or b.s <= 0.10 or hunger_wake or nap_done:
                    self._finish(t)

            # --- 空闲就决策 ---
            if self.action is None and not b.dead:
                self._choose(t)

        if b.dead:
            self.log(t, "dead", cause=b.death_cause)

        return self.result()

    # ------------------------------------------------------------------
    def result(self) -> dict:
        s = self.stats
        b = self.body
        minutes = max(1, s["minutes"])
        days_alive = minutes / P.MIN_PER_DAY
        feats = self._features(minutes, days_alive)
        return dict(
            seed=self.seed,
            lesion=list(self.lesion),
            edges_off=list(self.edges_off),
            noise_seed=self.noise_seed,
            mode=self.mode,
            challenge=self.challenge,
            survived=(not b.dead) and minutes >= self.days * P.MIN_PER_DAY - 5,
            days_alive=round(days_alive, 3),
            death=b.death_cause,
            chronic={k: round(v, 2) for k, v in b.chronic.items()},
            death_day=round((b.death_t - self.world.start) / P.MIN_PER_DAY, 2) if b.death_t else None,
            features=[float(x) for x in feats],
            mean_D=float(self._mean_D()),
            mean_state={k: round(v / max(1, self._d_n), 3) for k, v in self._x_sum.items()},
            lonely_max=round(getattr(self, "_l_max", 0.0), 3),
            stats={k: (v if not isinstance(v, list) else list(v)) for k, v in s.items()},
            daily=self.daily,
            events=self.events,
        )

    def _mean_D(self) -> float:
        return float(self._d_sum / max(1, self._d_n))

    def _features(self, minutes: float, days_alive: float):
        s = self.stats
        act = s["act"]
        ons = s["onsets"]
        if ons:
            sin_m = float(np.mean([math.sin(2 * math.pi * h / 24) for h in ons]))
            cos_m = float(np.mean([math.cos(2 * math.pi * h / 24) for h in ons]))
        else:
            sin_m = cos_m = 0.0
        day_act = s["active_day"]
        night_act = s["active_night"]
        return [
            (s["asleep"] / 60.0) / days_alive,
            s["bouts"] / days_alive,
            sin_m,
            cos_m,
            s["meals"] / days_alive,
            s["socials"] / days_alive,
            (s["out"] / 60.0) / days_alive,
            (s["night_awake"] / 60.0) / days_alive,
            s["flees"] / days_alive,
            (s["sick"] / 60.0) / days_alive,
        ]


def run_one(seed: int, lesion=(), noise_seed: int = 0,
            policy_mode: str = "allostatic", days: int = P.DAYS) -> dict:
    return Sim(seed, lesion, noise_seed, policy_mode, days).run()
