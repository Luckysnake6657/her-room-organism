# -*- coding: utf-8 -*-
"""会话回路：把机体、简报、嘴、形式、结算、存档接成一条能跑的线。

一轮 `say()` 做这些事（顺序不能乱）：
1. 如果是"主动查结算"的问法 → 只给世界账 + 强制披露，**不推**；
2. 否则算一次"有回应的接触"（带冷却，刷屏不算多次）→ 机体舒缓 + 慢性回落 + U 暂停；
3. 生成简报 → 嘴写一句 → 截断/越界替换；
4. 按形式延迟推进模拟时间（聊天期间她也在过日子）；
5. 存档。

用法（演示）：
    python -m organism.chat --save evidence/p3/session.json
"""
import argparse
import json
import os
import time

from . import absence, brief as B, drift, forget, intent, metamemory, notebook, organ, relation, retrieval, working
from . import claims, mouth, persist, settlement
from . import params as P
from .sim import Sim

SETTLE_KEYS = ("这段时间", "我不在", "你不在", "结算", "这几天怎么样")


class Session:
    def __init__(self, path: str = None, dry: bool = False, seed: int = 7,
                 persona=None, mode: str = "acquaintance", notebook=None):
        self.path = path
        self.dry = dry
        self.persona = persona
        self.mode = mode
        self.notebook = notebook
        self.last_gap = None
        self._last_contact_t = -10 ** 9
        self._asked_settlement = False
        self._initiated_day = -1
        self._present = True
        self._away_since = None
        self.last_absence = None
        self._away_before = None
        if path and os.path.exists(path):
            self.sim = persist.load(path)
            before = self.sim.t
            persist.resume(self.sim)          # 按挂钟补算
            self.last_gap = self.sim.last_gap
            self.last_absence = (absence.from_gap(self.last_gap, "closed")
                                 if self.last_gap else None)
        else:
            self.sim = Sim(seed, (), 1000 + seed, "allostatic", 180, product=True)
            self.sim.run(stop=self.sim.t + 60)  # 开机先过一小时
        self.seed = seed
        self._last_week = int(self.sim.t // (7 * P.MIN_PER_DAY))
        self._open_at = self.sim.t
        self._open_stats = dict(
            meals=self.sim.stats["meals"], socials=self.sim.stats["socials"],
            threats=self.sim.stats["threats"], sick=self.sim.stats["sick"],
            missed=self.sim.stats.get("missed_windows", 0))

    def _gap_since_open(self) -> dict:
        st = self._open_stats
        return dict(
            days_alone=round((self.sim.t - self._open_at) / P.MIN_PER_DAY, 2),
            meals=self.sim.stats["meals"] - st["meals"],
            socials=self.sim.stats["socials"] - st["socials"],
            threats=self.sim.stats["threats"] - st["threats"],
            sick_minutes=self.sim.stats["sick"] - st["sick"],
            missed_windows=self.sim.stats.get("missed_windows", 0) - st["missed"],
        )

    # ------------------------------------------------------------------
    def _is_settlement_query(self, text: str) -> bool:
        return any(k in text for k in SETTLE_KEYS)

    def _save(self):
        if self.path:
            persist.save(self.sim, self.path)

    # ------------------------------------------------------------------
    def say(self, text: str) -> dict:
        body = self.sim.body

        if self._is_settlement_query(text):
            if self.last_absence and self.last_absence["long"]:
                gap = self.last_absence["gap"]
            else:
                gap = self.last_gap or self._gap_since_open()
            return dict(text=settlement.text_for(gap) + claims.DISCLOSURE,
                        delay_s=8.0, proactive=False, kind="settlement")

        cooldown = P.MIN_PER_DAY / 4
        contact = (self.sim.t - self._last_contact_t) >= cooldown
        if contact:
            body.tend()
            self._last_contact_t = self.sim.t

        scored = retrieval.retrieve(self.notebook, text) if self.notebook else []
        nb = [e for _, e in scored]
        for _, e in scored:
            forget.touch(e)
        tier = metamemory.tier_of(scored)
        day_now = self.sim.world.day_at(self.sim.t)
        if day_now != getattr(self, "_last_regard_day", -1):
            relation.update(body, text, self.mode)
            self._last_regard_day = day_now
        br = B.make(body, facts=B.day_facts(self.sim), persona=self.persona,
                    mode=self.mode, notebook_entries=nb, recent=self.sim.body.working,
                    memory_tier=tier)
        asked = any(m in text for m in notebook.QUERY_MARKERS + notebook.WH_MARKERS)
        it = intent.decide(body, memory_tier=tier, asked_memory=asked,
                           proactive_ok=br["wants"].startswith("想主动"))
        if self.dry and it["move"] not in ("refuse", "recall"):
            out = dict(text="嗯。", delay_s=br["delay_s"], proactive=False,
                       raw="", replaced=False, hits=[])
        else:
            out = organ.render(it, br, text)

        # 聊天期间她也在过日子：按延迟推进，至少一分钟
        self.sim.run(stop=self.sim.t + max(1, int(round(out["delay_s"] / 60.0))))
        working.add(self.sim.body.working, "user", text, self.sim.t)
        working.add(self.sim.body.working, "her", out["text"], self.sim.t)
        self._maybe_weekly()
        self._save()
        return dict(text=out["text"], delay_s=out["delay_s"],
                    proactive=out["proactive"], kind="reply", contact=contact,
                    used_api=out.get("used_api", False), offline=out.get("offline", False))

    # ------------------------------------------------------------------
    def _maybe_weekly(self):
        """跨周就结算一次性格漂移：这一周她对你的看法净变了多少。"""
        wk = int(self.sim.t // (7 * P.MIN_PER_DAY))
        if wk == self._last_week:
            return
        drift.weekly(self.sim.body, self.sim.body.regard_week)
        self.sim.body.regard_week = 0.0
        self._last_week = wk

    # ------------------------------------------------------------------
    def ask(self, text: str, now: float = None):
        """立即生成，但不马上给——按形式延迟释放。宿主轮询 poll()。"""
        import time as _time
        now = _time.monotonic() if now is None else now
        r = self.say(text)
        self._pending = dict(reply=r, due=now + r["delay_s"])
        return r

    def poll(self, now: float = None):
        import time as _time
        now = _time.monotonic() if now is None else now
        if not self._pending:
            return None
        if now >= self._pending["due"]:
            r = self._pending["reply"]
            self._pending = None
            return r
        return None

    # ------------------------------------------------------------------
    def on_presence(self, present: bool, now: float = None) -> dict:
        """宿主（托盘/GUI）轮询"你在不在"时调用。

        离开期间模拟时间照走（她继续过日子），但不产生接触；
        回来不自动算接触——要等她真的被回应（say）。
        """
        import time as _time
        now = _time.monotonic() if now is None else now
        if present and not self._present:
            away = now - (self._away_since or now)
            self.sim.run(stop=self.sim.t + max(0, int(away / 60.0 * P.SIM_MIN_PER_REAL_MIN)))
            self.last_absence = absence.from_window(
                self.sim, self._away_before or absence.stats_now(self.sim), away / 60.0)
            self._present = True
            self._away_since = None
            self._away_before = None
            self._save()
            return dict(event="back", away_s=round(away, 1))
        if not present and self._present:
            self._present = False
            self._away_since = now
            self._away_before = absence.stats_now(self.sim)
            return dict(event="away")
        return dict(event="unchanged", present=self._present)

    # ------------------------------------------------------------------
    def greeting(self):
        """她先开口。只在孤独高、慢性低、且今天还没主动过时发生。

        不做 double-text：主动一次没被回应，当天不再追第二条。
        """
        from . import form as F
        f = F.form_of(self.sim.body, persona=self.persona)
        day = self.sim.world.day_at(self.sim.t)
        if not f["proactive"] or self._initiated_day == day:
            return None
        self._initiated_day = day
        nb = self.notebook.retrieve("") if self.notebook else []
        br = B.make(self.sim.body, persona=self.persona, mode=self.mode,
                    notebook_entries=nb)
        if self.dry:
            out = dict(text="（她先开口）", delay_s=br["delay_s"], proactive=True)
        else:
            out = mouth.initiate(br)
        self.sim.run(stop=self.sim.t + max(1, int(round(out["delay_s"] / 60.0))))
        self._save()
        return dict(text=out["text"], delay_s=out["delay_s"], kind="initiate")

    # ------------------------------------------------------------------
    def peek(self) -> dict:
        br = B.make(self.sim.body, persona=self.persona, mode=self.mode)
        return dict(state=br["state"], wants=br["wants"],
                    u=round(self.sim.body.u, 3), gap=self.last_gap)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", default="evidence/p3/session.json")
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args(argv)

    s = Session(args.save, dry=args.dry)
    print("（输入 exit 退出；问“这段时间”给结算）")
    while True:
        try:
            line = input("你：").strip()
        except EOFError:
            break
        if line in ("exit", "quit", ""):
            break
        r = s.say(line)
        print("（延迟 %.0f 秒）她：%s" % (r["delay_s"], r["text"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
