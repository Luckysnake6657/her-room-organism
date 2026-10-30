# -*- coding: utf-8 -*-
"""P0 政策：预测性稳态（allostasis），不是学习策略。

为什么 P0 用手写前向模型
------------------------
HANDOFF 要求「D 与奖励按 HRRL 公式」。这一版里：
* 奖励确实是 HRRL 的：r_t = D(H_t) - D(H_{t+1})，由身体算，不写死。
* 但策略用了一个手写的前向模型做一步预测（"提前行动"），
  没有用 Q-learning。这是有意的取舍：P0 要先把「六系统是否缺一不可」测出来，
  学习策略会多一层「没学会」的混淆。学习版留到 P1，单独预注册。

政策看得见什么
--------------
只看身体读数（六个变量）、当前位置、食物存量、是否傍晚（人的作息她知道的，
但今天来没来她不知道）。看不见世界的危险率，也看不见自己会怎么死。
"""
import math

import numpy as np

from . import params as P

SLEEP_PROPENSITY_MIN = P.SLEEP_PROPENSITY_MIN
SLEEP_NIGHT_WEIGHT = P.SLEEP_NIGHT_WEIGHT


def sleep_propensity(body) -> float:
    if "clock" in body.lesion:
        night = 0.5
    else:
        night = 0.5 + 0.5 * math.cos(2.0 * math.pi * (body.phi - 1.0) / 24.0)
    p = body.s + SLEEP_NIGHT_WEIGHT * night
    if "stress" not in body.lesion:
        p -= P.SLEEP_STRESS_PENALTY * max(0.0, body.a - 0.45)
    return p


class Policy:
    def __init__(self, rng: np.random.Generator, mode: str = "allostatic"):
        self.rng = rng
        self.mode = mode

    # ------------------------------------------------------------------
    @staticmethod
    def _option(kind, dur, value, **kw):
        d = dict(kind=kind, dur=int(round(dur)), value=float(value))
        d.update(kw)
        return d

    def _sleep_value(self, body, world, dur, place, hour):
        pred = body.predict(
            dur, asleep=True, active=False,
            cold=world.cold(place, hour), hour=hour + dur / 120.0,
            light=P.LIGHT_ASLEEP, place=place)
        v = body.D() - body.D_from(pred)
        if place != P.HOME:
            v -= P.SLEEP_AWAY_PENALTY
        return v

    def _eat_value(self, body, world, place, hour, malaise):
        pred = body.predict(
            P.MEAL_MIN, asleep=False, active=True,
            cold=world.cold(place, hour + 0.25), hour=hour + 0.25,
            light=P.LIGHT_OUT, eat=True, place=place)
        direct = body.D() - body.D_from(pred)

        # 前瞻（allostasis）：这一顿不吃，未来几小时能量会掉到哪
        if "energy" in body.lesion:
            future = 0.0
        else:
            vals = body.values()
            drain = P.E_DRAIN_AWAKE_H * 1.2
            h = P.EAT_ANTICIPATE_H
            e_no = max(0.0, body.e - drain * h)
            e_yes = min(1.0, body.e + P.MEAL_GAIN - drain * h)
            future = (body.D_from(dict(vals, energy=e_no))
                      - body.D_from(dict(vals, energy=e_yes)))
        u = direct + P.EAT_ANTICIPATE_W * future - P.EFFORT_ACTIVE * malaise
        if "stress" not in body.lesion and "stress_appetite" not in body.edges_off:
            u -= P.STRESS_APPETITE_COEF * body.a
        if "energy" not in body.lesion and body.e < 0.25:
            u += 0.40          # 饿极了：顾不上舒服不舒服
        return u

    def _social_value(self, body, world, place, hour, malaise, stress):
        pred = body.predict(
            40, asleep=False, active=False,
            cold=world.cold(place, hour + 0.33), hour=hour + 0.33,
            light=P.LIGHT_PORCH, social=True, place=place)
        v = body.D() - body.D_from(pred) - P.EFFORT_ACTIVE * malaise
        if "stress" not in body.lesion and "stress_social" not in body.edges_off:
            v += P.STRESS_SOCIAL_COEF * max(0.0, stress - P.STRESS_SOCIAL_THRESH)
        return v

    # ------------------------------------------------------------------
    def options(self, body, world, t: int) -> list:
        place = world.place
        hour = world.hour_at(t)
        d0 = body.D()
        opts = []

        i = 0.0 if "immune" in body.lesion else body.i
        malaise = 1.0 + P.I_MALAISE * i     # 生病时做什么都更费劲
        stress = 0.0 if "stress" in body.lesion else body.a
        comfort = P.HOME_COMFORT if place == P.HOME else 0.0
        rest_bonus = P.REST_IMMUNE_BONUS * i

        # ---- 本地 ----
        if place == P.FOOD and world.food_available():
            u = self._eat_value(body, world, place, hour, malaise) + comfort
            if u > P.MIN_ACTION_VALUE:
                opts.append(self._option("eat", P.MEAL_MIN, u, dest=place,
                                         active=True, eat=True))

        if sleep_propensity(body) > SLEEP_PROPENSITY_MIN and "sleep" not in body.lesion:
            dur = min(P.SLEEP_MAX_MIN, max(60.0, (body.s - 0.18) / P.S_CLEAR_H * 60.0))
            u = self._sleep_value(body, world, dur, place, hour) + comfort
            opts.append(self._option("sleep", dur, u, dest=place, asleep=True))

        if place == P.PORCH and world.person_likely(t):
            u = self._social_value(body, world, place, hour, malaise, stress) + comfort
            if u > P.MIN_ACTION_VALUE:
                opts.append(self._option("social", 40, u, dest=place,
                                         social=True, active=False))

        pred = body.predict(P.REST_MIN, asleep=False, active=False,
                            cold=world.cold(place, hour), hour=hour + 0.5,
                            light=world.light(place, False), place=place)
        opts.append(self._option("rest", P.REST_MIN,
                                 d0 - body.D_from(pred) + comfort + rest_bonus, dest=place))

        # ---- 去别处：只有目的地确实有「现在需要的事」才去 ----
        for dest in range(P.N_PLACES):
            if dest == place:
                continue
            best = 0.0
            if dest == P.FOOD and world.food_available():
                best = max(best, self._eat_value(body, world, dest, hour, malaise))
            if dest == P.PORCH and world.person_likely(t):
                best = max(best, self._social_value(body, world, dest, hour, malaise, stress))
            if dest == P.HOME and "sleep" not in body.lesion:
                if sleep_propensity(body) > SLEEP_PROPENSITY_MIN:
                    dur = min(P.SLEEP_MAX_MIN, max(60.0, (body.s - 0.18) / P.S_CLEAR_H * 60.0))
                    best = max(best, self._sleep_value(body, world, dur, P.HOME, hour))
                # 没别的事就想回屋：这是「家」的亲和力，不是需要
                best = max(best, 2.0 * P.HOME_COMFORT)
            if best <= P.MIN_ACTION_VALUE:
                continue

            hops = P.HOPS[place][dest]
            dur = hops * P.TRAVEL_MIN_PER_HOP
            travel_cold = 0.5 * (world.cold(place, hour) + world.cold(dest, hour + dur / 120.0))
            pred_t = body.predict(dur, asleep=False, active=True, cold=travel_cold,
                                  hour=hour + dur / 120.0, light=P.LIGHT_OUT, place=dest)
            u = (d0 - body.D_from(pred_t)) - P.EFFORT_HOP * hops * malaise
            u += P.DEST_DISCOUNT * best
            if dest != P.HOME and "stress_avoid" not in body.edges_off:
                u -= P.STRESS_AVOID_COEF * max(0.0, stress - P.STRESS_AVOID_THRESH)
            opts.append(self._option("goto", dur, u, dest=dest, active=True))

        # 兜底：永远至少有 rest
        if not opts:
            opts.append(self._option("rest", P.REST_MIN, 0.0, dest=place))
        return opts

    # ------------------------------------------------------------------
    def choose(self, body, world, t: int) -> dict:
        opts = self.options(body, world, t)
        if self.mode == "shuffle":
            pick = opts[int(self.rng.integers(len(opts)))]
        else:
            vals = np.array([o["value"] for o in opts], dtype=float)
            g = self.rng.gumbel(0.0, 1.0, size=len(vals))
            pick = opts[int(np.argmax(vals / P.SOFTMAX_TAU + g))]

        act = {k: v for k, v in pick.items() if k != "value"}
        act["end"] = t + act["dur"]
        act["start"] = t
        if act["kind"] == "sleep":
            h = world.hour_at(t)
            act["nap"] = bool(9.0 <= h < 18.0)
        return act
