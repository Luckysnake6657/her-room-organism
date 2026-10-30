# -*- coding: utf-8 -*-
"""原生她：身体 + 意图 + 器官 + 她的人格/记忆，跑在 organism 里（不挂 DSH）。

    python -m organism.native --data evidence/p3/cmw_native --import-dir evidence/p3/cmw_import

先本地跑通，再谈 QQ 通道。
"""
import argparse
import datetime as dt
import json
import os
import threading
import time

from . import (absence, attachment, brief as B, consolidate, drift, forget,
               form as F, habits, intent, legacy, memorize, notebook,
               params as P, persist, relation, retrieval, working)
from .model import Body
from .sim import Sim


class Native:
    def __init__(self, data_dir: str, import_dir: str, tick: bool = True,
                 grow: bool = True):
        os.makedirs(data_dir, exist_ok=True)
        self.path = os.path.join(data_dir, "session.json")
        self.nb_path = os.path.join(data_dir, "notebook.json")
        self.lock = threading.RLock()
        with open(os.path.join(import_dir, "persona.json"), encoding="utf-8") as f:
            p = json.load(f)
        self.persona = legacy.LegacyPersona(p["card"], p.get("name", "她"),
                                            words_base=p.get("words_base", 13))
        if os.path.exists(self.nb_path):
            self.nb = notebook.Notebook(self.nb_path)
        else:
            import shutil
            shutil.copy(os.path.join(import_dir, "notebook.json"), self.nb_path)
            self.nb = notebook.Notebook(self.nb_path)
        self.impressions = []
        self.mood = ""
        try:
            with open(os.path.join(import_dir, "impressions.json"), encoding="utf-8") as f:
                imp = json.load(f)
            self.impressions = [str(x.get("text") or "") for x in imp if x.get("text")]
        except Exception:
            pass
        try:
            with open(os.path.join(import_dir, "mood.json"), encoding="utf-8") as f:
                self.mood = str((json.load(f) or {}).get("text") or "")
        except Exception:
            pass
        self.pending_gap = None
        if os.path.exists(self.path):
            self.sim = persist.load(self.path)
            saved = getattr(self.sim, "saved_at", time.time())
            gap_min = max(0.0, (time.time() - saved) / 60.0)
            before = self._snap(self.sim)
            persist.resume(self.sim)
            if gap_min >= P.MIN_PER_DAY:
                self.pending_gap = absence.from_window(self.sim, before, gap_min)
        else:
            self.sim = Sim(7, (), 1007, "allostatic", 365, product=True)
            self.sim.run(stop=self.sim.t + 1)
            self.sim.body.working = []
            self.pending_gap = None
        self._last = time.monotonic()
        self._last_day = -1
        self._last_grow_day = -1
        self._last_grow_week = -1
        self.epoch = dt.datetime.now()
        self._grow_enabled = bool(grow)
        if self._grow_enabled:
            self._grow()
        self._tick_stop = False
        self.pending_proactive = False
        self._last_contact = time.time()
        self._last_recall = None
        if tick:
            threading.Thread(target=self._tick_loop, daemon=True).start()

    @staticmethod
    def _snap(sim) -> dict:
        return dict(meals=sim.stats["meals"], socials=sim.stats["socials"],
                    threats=sim.stats["threats"], sick=sim.stats["sick"],
                    missed=sim.stats.get("missed_windows", 0))

    def _tick_loop(self):
        while not self._tick_stop:
            time.sleep(30)
            with self.lock:
                self._advance()
                persist.save(self.sim, self.path)

    def close(self):
        self._tick_stop = True
        persist.save(self.sim, self.path)
        self.nb.save()

    def _advance(self):
        now = time.monotonic()
        m = int((now - self._last) / 60.0)
        if m > 0:
            self.sim.body.tend()
            self._last = now
            self.sim.run(stop=self.sim.t + int(m * P.SIM_MIN_PER_REAL_MIN))
            if self._grow_enabled:
                self._grow()

    def _grow(self):
        """过了一天就长一次；过了一周再长一次。时间用模拟时间，不用墙钟。"""
        day = self.sim.world.day_at(self.sim.t)
        if day == self._last_grow_day:
            return
        self._last_grow_day = day
        now = self.sim_now()
        forget.sweep(self.nb, now=now)
        for c in consolidate.candidates(self.nb, now=now):
            e = consolidate.apply(self.nb, c)
            if e is not None:
                e["created_at"] = now.strftime("%Y-%m-%dT%H:%M:%S")
        self.habits = habits.detect(self.nb, now=now)
        self._diary(day)
        if day // 7 != self._last_grow_week:
            self._last_grow_week = day // 7
            b = self.sim.body
            delta = b.regard - getattr(b, "regard_week", b.regard)
            drift.weekly(b, delta)
        self.nb.save()
        persist.save(self.sim, self.path)

    def sim_now(self):
        """模拟时间对应的日期：条目和窗口都用它，别用墙钟。"""
        return self.epoch + dt.timedelta(minutes=self.sim.t)

    def _diary(self, day: int):
        path = os.path.join(os.path.dirname(self.path), "diary.md")
        facts = B.day_facts(self.sim)
        with open(path, "a", encoding="utf-8") as f:
            f.write("## 第 %d 天\n%s\n\n" % (day, "；".join(facts)))

    def _writeback(self, text: str):
        """他说过、关于他自己的事 → 先进 pending，确认后才算记住。"""
        for fact in memorize.extract(text):
            e = self.nb.propose(fact, source="user")
            e["created_at"] = self.sim_now().strftime("%Y-%m-%dT%H:%M:%S")

    def maybe_proactive(self, quiet_hours: float = 3.0) -> bool:
        """孤独够高、状态够好、又安静够久 → 她可能先开口。"""
        with self.lock:
            if self.pending_proactive:
                return True
            if time.time() - self._last_contact < quiet_hours * 3600:
                return False
            f = F.form_of(self.sim.body, persona=self.persona)
            if not f["proactive"]:
                return False
            if not attachment.willing(self.sim.body, 0.0):
                return False
            self.pending_proactive = True
            return True

    def take_proactive(self, dry: bool = False) -> dict:
        """把"想先说一句"变成话；没有就返回 None。"""
        with self.lock:
            if not self.pending_proactive:
                return None
            self.pending_proactive = False
            self._last_contact = time.time()
            b = self.sim.body
            br = B.make(b, facts=B.day_facts(self.sim), persona=self.persona,
                        mode="acquaintance", notebook_entries=[],
                        recent=b.working, memory_tier="none")
            br["impressions"] = self.impressions
            br["mood"] = self.mood
            br["wants"] = "想主动说一句"
            if dry:
                out = dict(text="嗯。", delay_s=br["delay_s"], proactive=True)
            else:
                out = legacy.speak(br, "（你先开口）")
                out["proactive"] = True
                working.add(b.working, "her", out["text"])
            persist.save(self.sim, self.path)
            return out

    def pending(self) -> list:
        return [e for e in self.nb.live() if e["status"] == "pending"]

    def confirm(self, entry_id: int, yes: bool = True):
        with self.lock:
            out = self.nb.confirm(entry_id) if yes else self.nb.delete(entry_id)
            self.nb.save()
            return out

    ACK = {"没事", "嗯", "嗯嗯", "好", "好的", "行", "可以", "哈哈", "收到", "懂了", "睡了"}

    def respond(self, texts, dry: bool = False, bdi: bool = False):
        """按一串消息回一次；纯确认语可以不回。"""
        texts = [str(t).strip() for t in texts if str(t).strip()]
        if not texts:
            return None
        if all(t in self.ACK for t in texts):
            return None
        joined = "；".join(texts)
        info = None
        if bdi:
            from . import bdi as _bdi
            info = _bdi.extract(joined)
        out = self.say(joined, dry=dry, bdi=info)
        if info is not None and out is not None:
            out["bdi"] = info
        return out

    def ingest(self, texts, hers: str = ""):
        """把真实对话吃进记忆：不生成、不发送。"""
        with self.lock:
            self._last_contact = time.time()
            self._advance()
            b = self.sim.body
            b.tend()
            b.contact(None)
            for t in texts:
                t = str(t).strip()
                if not t:
                    continue
                self._writeback(t)
                relation.update(b, t)
                working.add(b.working, "user", t)
            hers = str(hers or "").strip()
            if hers:
                e = self.nb.add(hers, type="event", source="her", confidence=0.9)
                e["created_at"] = self.sim_now().strftime("%Y-%m-%dT%H:%M:%S")
                working.add(b.working, "her", hers)
            persist.save(self.sim, self.path)
            self.nb.save()

    def watch_ingest(self, state_path: str, interval: float = 20.0, once: bool = False):
        """只吃真实对话，不生成。"""
        wpath = os.path.join(os.path.dirname(self.path), "ingest.json")
        last = 0.0
        while True:
            try:
                with open(wpath, encoding="utf-8") as f:
                    last = float(json.load(f).get("last", 0.0))
            except Exception:
                last = 0.0
            try:
                st = json.load(open(state_path, encoding="utf-8"))
                msgs = (st.get("conversations", {}).get("private:owner", {})
                        .get("recentMessages") or [])
            except Exception:
                msgs = []
            new = [m for m in msgs if str(m.get("text") or "").strip()
                   and float(m.get("time") or 0) > last]
            new.sort(key=lambda m: float(m.get("time") or 0))
            for m in new:
                if m.get("isSelf"):
                    self.ingest([], m["text"])
                else:
                    self.ingest([m["text"]], "")
                last = float(m.get("time") or 0)
            with open(wpath, "w", encoding="utf-8") as f:
                json.dump(dict(last=last), f)
            if once:
                return
            time.sleep(interval)

    def watch(self, state_path: str, draft: bool = False, interval: float = 20.0,
              once: bool = False, quiet_ms: float = 60000.0, bdi: bool = False):
        """影子：读她收到的私聊，native 只生成、不发送。"""
        wpath = os.path.join(os.path.dirname(self.path), "watch.json")
        out_path = os.path.join(os.path.dirname(self.path), "drafts.jsonl")
        last = 0.0
        if os.path.exists(wpath):
            try:
                with open(wpath, encoding="utf-8") as f:
                    last = float(json.load(f).get("last", 0.0))
            except Exception:
                last = 0.0
        pending = []
        while True:
            try:
                with open(state_path, encoding="utf-8") as f:
                    st = json.load(f)
                conv = st.get("conversations", {}).get("private:owner", {})
                msgs = [m for m in (conv.get("recentMessages") or [])
                        if not m.get("isSelf") and str(m.get("text") or "").strip()]
            except Exception:
                msgs = []
            new = [m for m in msgs if float(m.get("time") or 0) > last]
            for m in new:
                pending.append(m)
                last = max(last, float(m.get("time") or 0))
            if pending and (once or time.time() * 1000 - float(pending[-1].get("time") or 0) > quiet_ms):
                texts = [str(m.get("text")).strip() for m in pending]
                out = self.respond(texts, dry=not draft, bdi=bdi)
                with open(out_path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(dict(t=pending[-1].get("time"), text=" / ".join(texts),
                                            draft=out["text"] if out else "（没回）",
                                            bdi=(out.get("bdi") if out else None)),
                                       ensure_ascii=False) + "\n")
                print("影子 你：%s\n影子 她：%s" % (" / ".join(texts),
                                                  out["text"] if out else "（没回）"))
                pending = []
            with open(wpath, "w", encoding="utf-8") as f:
                json.dump(dict(last=last), f)
            if once:
                return
            if once:
                return
            time.sleep(interval)

    def say(self, text: str, dry: bool = False, bdi: dict = None) -> dict:
        with self.lock:
            self._last_contact = time.time()
            self._advance()
            b = self.sim.body
            if self._last_recall is not None:
                if memorize.is_no(text):
                    self.nb.record_outcome(self._last_recall, False)
                elif memorize.is_yes(text):
                    self.nb.record_outcome(self._last_recall, True)
                self._last_recall = None
            b.tend()
            b.contact(None)
            day = self.sim.world.day_at(self.sim.t)
            if day != self._last_day:
                relation.update(b, text)
                self._last_day = day
            scored = retrieval.retrieve(self.nb, text)
            nb = [e for _, e in scored]
            for _, e in scored:
                forget.touch(e)
            from . import metamemory
            tier = metamemory.tier_of(scored)
            gap = self.pending_gap["gap"] if self.pending_gap else None
            br = B.make(b, gap=gap, facts=B.day_facts(self.sim), persona=self.persona,
                        mode="acquaintance", notebook_entries=nb,
                        recent=b.working, memory_tier=tier)
            br["impressions"] = self.impressions
            br["mood"] = self.mood
            br["bdi"] = bdi
            self.pending_gap = None
            asked = any(m in text for m in notebook.QUERY_MARKERS + notebook.WH_MARKERS)
            it = intent.decide(b, memory_tier=tier, asked_memory=asked,
                               proactive_ok=br["wants"].startswith("想主动"))
            from . import engagement
            eng = engagement.price(b, text)
            br["mode"] = "task" if eng["decision"] == "now" else "life"
            br["engagement"] = eng
            if eng["decision"] == "later":
                persist.save(self.sim, self.path)
                self.nb.save()
                return dict(text="现在有点累，晚点行吗", delay_s=br["delay_s"],
                            replaced=True, mode="later")
            if eng["decision"] == "brief":
                br["words"] = max(12, min(int(br["words"]), 20))
            br["no_question"] = it.get("no_question", False)
            if it["move"] == "refuse":
                out = dict(text=notebook.REFUSAL, delay_s=br["delay_s"], replaced=True)
            elif it["move"] == "recall" and nb:
                e = nb[0]
                self._last_recall = e
                t = ("我好像记得，" + e["text"]) if tier == "fuzzy" else notebook.quote(e)
                out = dict(text=t, delay_s=br["delay_s"], replaced=True)
            elif dry:
                out = dict(text="嗯。", delay_s=br["delay_s"], replaced=False)
            else:
                out = legacy.speak(br, text)
            self._writeback(text)
            working.add(b.working, "user", text)
            if not dry:
                working.add(b.working, "her", out["text"])
            persist.save(self.sim, self.path)
            self.nb.save()
            return out
        return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="evidence/p3/cmw_native")
    ap.add_argument("--import-dir", default="evidence/p3/cmw_import")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--watch", default=None, help="影子模式：读这个 state 文件里的私聊")
    ap.add_argument("--draft", action="store_true", help="影子模式下真的生成草稿（默认 dry）")
    ap.add_argument("--bdi", action="store_true", help="生成前先抽他的处境")
    args = ap.parse_args(argv)
    n = Native(args.data, args.import_dir)
    if args.watch:
        n.watch(args.watch, draft=args.draft, bdi=args.bdi)
        return 0
    print("原生她：身体 t=%s 状态=%s；本子 %d 条" % (
        n.sim.t, B.state_phrase(n.sim.body), len(n.nb.live())))
    print("命令：/pending 看待确认 /yes <id> 确认 /no <id> 删掉 /exit 退出")
    while True:
        try:
            text = input("你：").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text in ("/exit", "/quit"):
            break
        if text == "/pending":
            for e in n.pending():
                print("  #%s %s" % (e["id"], e["text"]))
            continue
        if text.startswith("/yes ") or text.startswith("/no "):
            try:
                eid = int(text.split()[1])
            except Exception:
                print("  用法：/yes 12")
                continue
            n.confirm(eid, yes=text.startswith("/yes"))
            print("  好")
            continue
        out = n.say(text, dry=args.dry)
        wait = min(float(out.get("delay_s", 0)), 10.0)
        if wait > 0:
            time.sleep(wait)
        print("她：%s" % out["text"])
    persist.save(n.sim, n.path)
    n.nb.save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
