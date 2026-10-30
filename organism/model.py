# -*- coding: utf-8 -*-
"""身体（六系统）与世界（温度/食物/危险/人）。

设计原则
--------
1. 六个系统各有自己的时间常数，互相耦合；没有哪个是「音量旋钮」。
2. 效价 D 由身体自己算：D = sqrt(Σ w_k ((dev_k)/scale_k)^2)，
   其中 dev 只取「坏的方向」。
3. 拆掉一个系统 = 冻结它的状态 + 切断它的耦合 + 让它不参与 D + 政策看不见它。
   这是消融实验的唯一定义，六个系统用同一套开关。
4. 世界的外生随机数**预生成**（同一 seed 下所有条件共用同一串威胁/感染抽签），
   这样消融和基线是配对比较，而不是两次不同的运气。
"""
import math

import numpy as np

from . import params as P


def circ_dist_h(a: float, b: float) -> float:
    """两个「小时」在 24h 环上的最短距离。"""
    return abs((a - b + 12.0) % 24.0 - 12.0)


class Body:
    """六个变量 + 设定点 + 存活区间 + D + 奖励。"""

    def __init__(self, lesion=(), edges_off=(), product: bool = False):
        self.lesion = frozenset(lesion)
        self.edges_off = frozenset(edges_off)
        self.product = bool(product)
        # 慢性程度 0..3（连续值）。产品版里越界会把它推高，恢复很慢，照护能加速。
        self.chronic = dict(energy=0.0, stress=0.0, immune=0.0)
        self.oor_accum = dict(energy=0.0, stress=0.0, immune=0.0)
        # 不可补的损失账：错过的窗口、独处的天数。只记账，不额外加罚。
        self.losses = dict(missed_windows=0, days_alone=0.0)
        # 慢参数：关系解绑度 U（0..U_MAX）。只调制表达，不改状态。
        self.u = 0.0
        # 关系态度：她对你的看法（0..1，0.5 起）。只改形式与立场，不改身体。
        self.regard = 0.5
        self.regard_log = []
        self.regard_week = 0.0
        self.trait_drift = 0.0
        self.trait_log = []
        # 工作记忆：最近 7±2 轮原文（跨轮指代用）
        self.working = []
        self._contact_today = False
        self.e = P.E_INIT
        self.s = P.S_INIT
        self.a = P.A_INIT
        self.i = P.I_INIT
        self.l = P.L_INIT
        self.phi = P.PHI_INIT

        # 炎症负荷与感染增益（慢变量）
        self.load = 0.0
        self.infect = 0.0

        # 出界累计（分钟）与死因
        self.oor = {k: 0.0 for k in P.TERMINAL_MIN}
        self.dead = False
        self.death_cause = None
        self.death_t = None

        self._d_prev = self.D()

    # ------------------------------------------------------------------
    # 状态
    # ------------------------------------------------------------------
    def values(self) -> dict:
        hour = getattr(self, "_hour", P.T_START_MIN / 60.0)
        mis = 0.0 if "clock" in self.lesion else circ_dist_h(self.phi, hour)
        return dict(
            energy=self.e,
            sleep=self.s,
            stress=self.a,
            immune=self.i,
            lonely=self.l,
            misalign=mis,
        )

    def _hour_now(self, hour: float) -> float:
        self._hour = hour % 24.0
        return self._hour

    def deviations(self) -> dict:
        v = self.values()
        dev = {
            "energy": max(0.0, P.SP["energy"] - v["energy"]),
            "sleep": max(0.0, v["sleep"] - P.SP["sleep"]),
            "stress": max(0.0, v["stress"] - P.SP["stress"]),
            "immune": max(0.0, v["immune"] - P.SP["immune"]),
            "lonely": max(0.0, v["lonely"] - P.SP["lonely"]),
            "misalign": abs(v["misalign"] - P.SP["misalign"]),
        }
        if "dummy" in self.lesion:
            dev["dummy"] = 0.0       # 化妆消融：只走一遍代码，不改任何动力学
        for k in ("energy", "sleep", "stress", "immune", "lonely", "misalign"):
            if k in self.lesion:
                dev[k] = 0.0
        return dev

    def D(self) -> float:
        return self.D_from(self.values())

    def D_from(self, vals: dict) -> float:
        dev = {
            "energy": max(0.0, P.SP["energy"] - vals["energy"]),
            "sleep": max(0.0, vals["sleep"] - P.SP["sleep"]),
            "stress": max(0.0, vals["stress"] - P.SP["stress"]),
            "immune": max(0.0, vals["immune"] - P.SP["immune"]),
            "lonely": max(0.0, vals["lonely"] - P.SP["lonely"]),
            "misalign": abs(vals["misalign"] - P.SP["misalign"]),
        }
        tot = 0.0
        for k, d in dev.items():
            if k in self.lesion:
                continue
            tot += P.WEIGHT.get(k, 0.0) * (d / P.SCALE.get(k, 1.0)) ** 2
        tot += P.CHRONIC_D * sum(getattr(self, "chronic", {}).values())
        return math.sqrt(tot)

    # ------------------------------------------------------------------
    # 动力学
    # ------------------------------------------------------------------
    def _gate(self) -> float:
        """内钟对睡眠压力的门控（均值 < 1，夜间窄峰）。"""
        if "clock" in self.lesion:
            return 1.0
        x = 0.5 + 0.5 * math.cos(2.0 * math.pi * (self.phi - P.GATE_CENTER_H) / 24.0)
        x = x ** P.GATE_POWER
        return P.GATE_TROUGH + (P.GATE_PEAK - P.GATE_TROUGH) * x

    def _react(self) -> float:
        """内钟对应激反应性的调制。"""
        if "clock" in self.lesion:
            return 1.0
        return 1.0 + P.A_REACTIVITY * math.cos(2.0 * math.pi * (self.phi - P.GATE_CENTER_H) / 24.0)

    def morning_signal(self) -> float:
        """晨间「醒得来」的高斯窗；拆掉昼夜系统后恒定 0.5。"""
        if "clock" in self.lesion:
            return 0.5
        d = circ_dist_h(self.phi, P.WAKE_CENTER_H)
        return math.exp(-0.5 * (d / P.WAKE_SIGMA_H) ** 2)

    def step(self, dt: float, ctx: dict) -> None:
        self._hour_now(ctx["hour"])
        hour = self._hour_now(ctx["hour"])
        asleep = bool(ctx["asleep"])
        active = bool(ctx["active"])
        cold = float(ctx["cold"])
        light = float(ctx["light"])
        place = int(ctx.get("place", P.HOME))

        i_eff = 0.0 if "immune" in self.lesion else self.i

        # 1) 内钟：自由运行略长于 24h，被光照牵引
        if "clock" not in self.lesion:
            dt_h = dt / 60.0
            self.phi = (self.phi + (24.0 / P.DAY_LEN_H) * dt_h) % 24.0
            err = math.sin(2.0 * math.pi * (hour - self.phi) / 24.0)
            self.phi = (self.phi + P.K_LIGHT_H * light * err * dt_h) % 24.0

        # 2) 能量
        if "energy" in self.lesion:
            self.e = P.SP["energy"]
        else:
            if asleep:
                drain = P.E_DRAIN_ASLEEP_H
            else:
                drain = P.E_DRAIN_AWAKE_H * (P.E_ACTIVE_MULT if active else 1.0)
            drain *= (1.0 + P.E_COLD_MULT * cold) * (1.0 + P.E_IMMUNE_MULT * i_eff)
            if "stress" not in self.lesion and "stress_energy" not in self.edges_off:
                drain *= 1.0 + P.STRESS_ENERGY_COEF * self.a
            self.e = max(0.0, self.e - drain * dt / 60.0)

        # 3) 睡眠压力
        if "sleep" in self.lesion:
            self.s = P.SP["sleep"]
        elif asleep:
            clear = P.S_CLEAR_H
            if place != P.HOME:
                clear *= P.SLEEP_OFFSITE_QUALITY
            if "stress" not in self.lesion and "stress_sleep" not in self.edges_off:
                clear *= max(0.35, 1.0 - P.STRESS_SLEEP_COEF * self.a)   # 心里有事，睡得浅
            clear *= 1.0 - P.S_IMMUNE_BLOCK * i_eff
            self.s = max(0.0, self.s - clear * dt / 60.0)
        else:
            self.s = min(
                1.0,
                self.s + P.S_RISE_H * self._gate() * (1.0 + 0.6 * i_eff) * dt / 60.0,
            )

        # 4) 应激
        if "stress" in self.lesion:
            self.a = P.SP["stress"]
        else:
            tone = 0.0
            if "energy" not in self.lesion and self.e < P.A_E_LOW_THRESH:
                tone += P.A_E_LOW_RISE_H * (P.A_E_LOW_THRESH - self.e) / P.A_E_LOW_THRESH
            if self.s > P.A_S_DEBT_THRESH:
                tone += P.A_S_DEBT_RISE_H * (self.s - P.A_S_DEBT_THRESH) / (1.0 - P.A_S_DEBT_THRESH)
            if "lonely" not in self.lesion and self.l > P.A_LONELY_THRESH:
                tone += P.A_LONELY_RISE_H * (self.l - P.A_LONELY_THRESH) / (1.0 - P.A_LONELY_THRESH)
            tone += P.A_COLD_RISE_H * cold * 0.5
            if place != P.HOME and (hour >= P.NIGHT_START_H or hour < P.NIGHT_END_H):
                tone += P.A_NIGHT_OUT_TONE_H
            tone += P.A_IMMUNE_RISE_H * i_eff
            tone += P.A_CAR_H * math.exp(
                -0.5 * ((hour - P.A_CAR_CENTER_H) / P.A_CAR_SIGMA_H) ** 2)
            self.a += (tone - (self.a - P.A_BASELINE) / P.A_TAU_H) * dt / 60.0
            self.a = min(1.0, max(0.0, self.a))

        # 5) 免疫 / 炎症
        if "immune" in self.lesion:
            self.i = P.SP["immune"]      # 冻结在设定点；下游一律按 0 使用
            self.load = 0.0
            self.infect = 0.0
        else:
            drive = P.I_ACTIVE_DRIVE * (1.0 if active else 0.0) + P.I_COLD_DRIVE * cold
            if (self.a > P.I_STRESS_THRESH and "stress_immune" not in self.edges_off
                    and "stress" not in self.lesion):
                drive += P.I_STRESS_DRIVE * (self.a - P.I_STRESS_THRESH) / (1.0 - P.I_STRESS_THRESH)
            dt_h = dt / 60.0
            self.load += drive * dt_h - self.load * dt_h / P.I_LOAD_TAU_H
            self.load = max(0.0, self.load)
            self.infect *= math.exp(-dt_h / P.I_INFECT_TAU_H)
            target = min(1.0, self.load + self.infect)
            self.i += (target - self.i) * (1.0 - math.exp(-dt_h / P.I_FOLLOW_TAU_H))

        # 6) 依恋 / 孤独
        if "lonely" in self.lesion:
            self.l = P.SP["lonely"]
        else:
            self.l = min(1.0, self.l + P.L_RISE_H * dt / 60.0)

        # 7) 慢参数：连续无回应的日子里，关系解绑度缓慢上升
        if not self._contact_today:
            self.u += (P.U_MAX - self.u) * (1.0 - 0.5 ** ((dt / 1440.0) / P.U_HALF_LIFE_DAYS))
            self.u = min(P.U_MAX, self.u)

        # 8) 存活
        self._check_viable(dt)

    def _check_viable(self, dt: float) -> None:
        vals = dict(energy=self.e, sleep=self.s, stress=self.a, immune=self.i)
        if self.product:
            # 产品版：不死。越界 → 夹回边界，慢性程度缓慢上推；不越界则极慢回落。
            for k, (lo, hi) in P.VIABLE.items():
                if k not in vals:
                    continue
                v = vals[k]
                out = v < lo or v > hi
                if k != "sleep":
                    if out:
                        self.oor_accum[k] = self.oor_accum.get(k, 0.0) + dt
                    else:
                        self.oor_accum[k] = self.oor_accum.get(k, 0.0) * (
                            1.0 - dt / (14.0 * 24.0 * 60.0))
                    self.chronic[k] = min(3.0, self.oor_accum.get(k, 0.0) / (24.0 * 60.0))
            return
            return
        for k, lim in P.TERMINAL_MIN.items():
            lo, hi = P.VIABLE[k]
            v = vals[k]
            bad = v < lo or v > hi
            self.oor[k] = self.oor[k] + dt if bad else 0.0
            if self.oor[k] >= lim and not self.dead:
                self.dead = True
                self.death_cause = k
                self.death_t = None
                return

    def _set_var(self, key: str, value: float) -> None:
        setattr(self, {"energy": "e", "sleep": "s", "stress": "a", "immune": "i"}[key], value)

    def record_loss(self, kind: str, n: float = 1.0) -> None:
        """记一笔补不回来的损失。不额外加惩罚——它已经通过状态产生了后果。"""
        self.losses[kind] = self.losses.get(kind, 0) + n

    def care(self, amount: float = None) -> None:
        """被照顾：慢性程度一次性往下压（P2 的形式通道调它）。"""
        amount = P.CARE_STRENGTH if amount is None else amount
        for k in self.chronic:
            self.chronic[k] = max(0.0, self.chronic[k] - amount)
            self.oor_accum[k] = self.chronic[k] * 24.0 * 60.0

    def tend(self, amount: float = None, u_drop: float = None) -> None:
        """一次"被回应"的完整效果：社交舒缓 + 慢性回落 + 解绑暂停。"""
        self.contact()
        self.care(amount)
        self._contact_today = True
        self.u = max(0.0, self.u - (P.U_CONTACT_DROP if u_drop is None else u_drop))

    # ------------------------------------------------------------------
    # 事件
    # ------------------------------------------------------------------
    def threat_hit(self, injury: bool) -> None:
        self.a = min(1.0, self.a + P.A_THREAT_JUMP * self._react())
        self.e = max(0.0, self.e - 0.02)
        if injury:
            self.infect = min(1.0, self.infect + 0.15)
            self.load += 0.10

    def infection(self) -> None:
        self.infect = min(1.0, self.infect + P.I_INFECT_JUMP)

    def contact(self, npc: bool = False) -> None:
        if "lonely" not in self.lesion:
            if npc:
                drop = (P.NPC_LONELY_RELIEF_PRODUCT if self.product
                        else P.NPC_LONELY_RELIEF)
            else:
                drop = P.L_CONTACT_DROP
            self.l = max(0.0, self.l - drop)
        self.a = max(0.0, self.a - P.A_CONTACT_RELIEF)

    def meal(self) -> None:
        if "energy" not in self.lesion:
            self.e = min(1.0, self.e + P.MEAL_GAIN)

    # ------------------------------------------------------------------
    # 预测（政策用的前向模型；和真实动力学同一套公式，单步）
    # ------------------------------------------------------------------
    def predict(self, dur_min: float, *, asleep: bool, active: bool, cold: float,
                hour: float, light: float, eat: bool = False, social: bool = False,
                place: int = P.HOME) -> dict:
        dt_h = dur_min / 60.0
        i_eff = 0.0 if "immune" in self.lesion else self.i
        e, s, a = self.e, self.s, self.a
        l = self.l
        phi = self.phi

        if "clock" not in self.lesion:
            phi = (phi + (24.0 / P.DAY_LEN_H) * dt_h) % 24.0
            err = math.sin(2.0 * math.pi * (hour - phi) / 24.0)
            phi = (phi + P.K_LIGHT_H * light * err * dt_h) % 24.0

        if "energy" not in self.lesion:
            drain = P.E_DRAIN_ASLEEP_H if asleep else P.E_DRAIN_AWAKE_H * (P.E_ACTIVE_MULT if active else 1.0)
            drain *= (1.0 + P.E_COLD_MULT * cold) * (1.0 + P.E_IMMUNE_MULT * i_eff)
            if "stress" not in self.lesion and "stress_energy" not in self.edges_off:
                drain *= 1.0 + P.STRESS_ENERGY_COEF * a
            e = max(0.0, e - drain * dt_h)
            if eat:
                e = min(1.0, e + P.MEAL_GAIN)

        if "sleep" not in self.lesion:
            if asleep:
                clear = P.S_CLEAR_H
                if place != P.HOME:
                    clear *= P.SLEEP_OFFSITE_QUALITY
                if "stress" not in self.lesion and "stress_sleep" not in self.edges_off:
                    clear *= max(0.35, 1.0 - P.STRESS_SLEEP_COEF * a)
                clear *= 1.0 - P.S_IMMUNE_BLOCK * i_eff
                s = max(0.0, s - clear * dt_h)
            else:
                gate = 1.0
                if "clock" not in self.lesion:
                    x = 0.5 + 0.5 * math.cos(2.0 * math.pi * (phi - P.GATE_CENTER_H) / 24.0)
                    x = x ** P.GATE_POWER
                    gate = P.GATE_TROUGH + (P.GATE_PEAK - P.GATE_TROUGH) * x
                s = min(1.0, s + P.S_RISE_H * gate * (1.0 + 0.6 * i_eff) * dt_h)

        if "stress" not in self.lesion:
            tone = 0.0
            if "energy" not in self.lesion and e < P.A_E_LOW_THRESH:
                tone += P.A_E_LOW_RISE_H * (P.A_E_LOW_THRESH - e) / P.A_E_LOW_THRESH
            if s > P.A_S_DEBT_THRESH:
                tone += P.A_S_DEBT_RISE_H * (s - P.A_S_DEBT_THRESH) / (1.0 - P.A_S_DEBT_THRESH)
            if "lonely" not in self.lesion and l > P.A_LONELY_THRESH:
                tone += P.A_LONELY_RISE_H * (l - P.A_LONELY_THRESH) / (1.0 - P.A_LONELY_THRESH)
            tone += P.A_COLD_RISE_H * cold * 0.5 + P.A_IMMUNE_RISE_H * i_eff
            if place != P.HOME and (hour >= P.NIGHT_START_H or hour < P.NIGHT_END_H):
                tone += P.A_NIGHT_OUT_TONE_H
            tone += P.A_CAR_H * math.exp(
                -0.5 * ((hour - P.A_CAR_CENTER_H) / P.A_CAR_SIGMA_H) ** 2)
            decay = math.exp(-dt_h / P.A_TAU_H)
            a = P.A_BASELINE + (a - P.A_BASELINE) * decay + tone * P.A_TAU_H * (1.0 - decay)
            a = min(1.0, max(0.0, a))
            if social:
                a = max(0.0, a - P.A_CONTACT_RELIEF)

        if "lonely" not in self.lesion:
            l = min(1.0, l + P.L_RISE_H * dt_h)
            if social:
                l = max(0.0, l - P.L_CONTACT_DROP)

        mis = 0.0 if "clock" in self.lesion else circ_dist_h(phi, hour)
        return dict(energy=e, sleep=s, stress=a, immune=self.i, lonely=l, misalign=mis)


class World:
    """四个地点的世界。外生随机数预生成，保证配对。"""

    def __init__(self, seed: int, days: int = P.DAYS, challenge=False):
        self.seed = int(seed)
        self.days = days
        self.challenge = challenge
        self.start = P.T_START_MIN
        self.end = self.start + days * P.MIN_PER_DAY
        n = self.end + 10
        rng = np.random.default_rng(seed)
        self.u_threat = rng.random(n)
        self.u_injury = rng.random(n)
        self.u_infect = rng.random(n)
        self.person_day = rng.random(days) < P.PERSON_P
        if challenge is True or challenge == "std":
            # 挑战周：所有条件在同一时刻挨同一场感染 + 同一场惊吓。
            # 这样「拆掉免疫/应激」才有东西可拆——好周里它们本来就该安静。
            self.u_infect[self.start + 2 * P.MIN_PER_DAY + 9 * 60] = 0.0
            self.u_threat[self.start + 4 * P.MIN_PER_DAY + 22 * 60] = 0.0
        if challenge == "dense":
            # 密集威胁周（P0b）：每天夜里都有一场，用来测「应激是不是只在威胁多时才管事」
            for d in range(days):
                self.u_threat[self.start + d * P.MIN_PER_DAY + 21 * 60] = 0.0
        self.food = P.FOOD_INIT
        self.place = P.HOME
        self.t = self.start
        self.threat_now = False
        self.threat_injury = False

    # -- 世界状态 ------------------------------------------------------
    def hour_at(self, t: int) -> float:
        return (t % P.MIN_PER_DAY) / 60.0

    def day_at(self, t: int) -> int:
        return max(0, min(self.days - 1, (t - self.start) // P.MIN_PER_DAY))

    def is_night(self, hour: float) -> bool:
        return hour >= P.NIGHT_START_H or hour < P.NIGHT_END_H

    def ambient_c(self, hour: float) -> float:
        return P.T_MEAN_C + P.T_AMP_C * math.cos(2.0 * math.pi * (hour - P.T_PEAK_H) / 24.0)

    def cold(self, place: int, hour: float) -> float:
        if place == P.HOME:
            return 0.02
        t = self.ambient_c(hour)
        return min(1.0, max(0.0, (P.T_HOME_C - t) / P.T_HOME_C))

    def light(self, place: int, asleep: bool) -> float:
        if asleep:
            return P.LIGHT_ASLEEP
        if place == P.HOME:
            return P.LIGHT_HOME
        if place == P.PORCH:
            return P.LIGHT_PORCH
        return P.LIGHT_OUT

    def person_present(self, t: int) -> bool:
        h = self.hour_at(t)
        return bool(P.PERSON_START_H <= h < P.PERSON_END_H and self.person_day[self.day_at(t)])

    def person_likely(self, t: int) -> bool:
        """她只知道「傍晚门廊一般有人」，不知道今天到底来没来。"""
        h = self.hour_at(t)
        return bool(P.PERSON_START_H <= h < P.PERSON_END_H)

    def food_available(self) -> bool:
        return self.food >= P.FOOD_MIN

    # -- 每分钟推进 ----------------------------------------------------
    def advance(self, body: Body, place: int, asleep: bool, dt: float, t: int) -> list:
        """推进世界一分钟，返回本分钟发生的事件（可能为空）。"""
        ev = []
        hour = self.hour_at(t)
        # 世界侧的信号：外生、与她的状态无关（不是状态读数）
        if abs(hour - 6.0) < 0.5 / 60.0:
            ev.append(dict(kind="dawn"))
        if abs(hour - 20.0) < 0.5 / 60.0:
            ev.append(dict(kind="dusk"))
        if abs(hour - 18.0) < 0.5 / 60.0:
            ev.append(dict(kind="person_arrives" if self.person_day[self.day_at(t)]
                          else "person_absent"))
        if abs(hour - 21.5) < 0.5 / 60.0 and self.person_day[self.day_at(t)]:
            ev.append(dict(kind="person_left"))
        if abs(hour - 3.0) < 0.5 / 60.0 and self.ambient_c(hour) < 8.0:
            ev.append(dict(kind="cold_snap"))
        # 食物点自己会长回来，跟她去不去无关（否则她不来就永远没得吃）
        self.food = min(1.0, self.food + P.FOOD_REGROW_H * dt / 60.0)

        night = self.is_night(hour)
        hazard = P.HAZARD[place][1 if night else 0]
        if not body.dead and self.u_threat[t] < hazard * dt / 60.0:
            injury = bool(self.u_injury[t] < P.A_INJURY_PROB)
            body.threat_hit(injury=injury)
            ev.append(dict(kind="threat", place=place, injury=injury))

        p_inf = P.I_INFECT_P_DAY / P.MIN_PER_DAY
        cold = self.cold(place, hour)
        p_inf *= 1.0 + 2.0 * cold
        if body.e < 0.30:
            p_inf *= 1.5
        if not body.dead and self.u_infect[t] < p_inf:
            body.infection()
            ev.append(dict(kind="infection", place=place))

        return ev
