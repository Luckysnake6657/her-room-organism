# -*- coding: utf-8 -*-
"""身体守护进程：她按真实时间一直活着，不等你发消息。

- 常驻：每 15 秒醒一次，把过去这段时间按 1:1 推进模拟
- 离线补算：启动时按挂钟补上关掉的时段
- 按 peer 独立存档：一个 peer 一个数据目录（现在只有你）
- 接口：
    GET  /health            → 现在几点、什么状态
    POST /form   {peer,text} → 状态 + 延迟 + 字数提示 + 主动倾向
    POST /reply  {peer,text} → 记下她说了什么（只做统计，不生成）
    POST /absence{peer,minutes} → 补算缺席，返回结算 + 披露

她的话仍由她自己的 DSH 写；这里只给身体。
"""
import argparse
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import absence, claims, form as F, params as P, persist, relation, settlement
from .sim import Sim

TICK_SEC = 15
SAVE_EVERY_MIN = 10


class Body:
    def __init__(self, home: str, peer: str = "owner", days: int = 365):
        self.home = home
        self.peer = peer
        os.makedirs(home, exist_ok=True)
        self.path = os.path.join(home, "body.json")
        if os.path.exists(self.path):
            self.sim = persist.load(self.path)
            persist.resume(self.sim)          # 按挂钟补算
        else:
            self.sim = Sim(7, (), 1007, "allostatic", days, product=True)
            self.sim.run(stop=self.sim.t + 1)
        self.lock = threading.Lock()
        self._last = time.monotonic()
        self._last_save = self.sim.t
        self.start = self.sim.t

    # ------------------------------------------------------------
    def advance(self):
        """把真实过去的时间推进到模拟里（1 分钟 = 1 分钟）。"""
        now = time.monotonic()
        minutes = int((now - self._last) / 60.0)
        if minutes <= 0:
            return
        self._last = now
        self.sim.run(stop=self.sim.t + minutes * P.SIM_MIN_PER_REAL_MIN)
        if self.sim.t - self._last_save >= SAVE_EVERY_MIN:
            persist.save(self.sim, self.path)
            self._last_save = self.sim.t

    def tick_loop(self):
        while True:
            time.sleep(TICK_SEC)
            with self.lock:
                self.advance()

    # ------------------------------------------------------------
    def health(self):
        b = self.sim.body
        return dict(t=self.sim.t, hour=round(self.sim.world.hour_at(self.sim.t), 2),
                    state=self._state(), D=round(b.D(), 3),
                    u=round(b.u, 3), regard=round(b.regard, 3),
                    drift=round(b.trait_drift, 3))

    def _state(self):
        from . import brief
        return brief.state_phrase(self.sim.body)

    def form(self, text: str, peer: str = None):
        with self.lock:
            self.advance()
            b = self.sim.body
            cooldown = P.MIN_PER_DAY / 4
            if self.sim.t - getattr(self, "_last_contact", -10 ** 9) >= cooldown:
                b.tend()
                self._last_contact = self.sim.t
            day_now = self.sim.world.day_at(self.sim.t)
            if day_now != getattr(self, "_last_regard_day", -1):
                relation.update(b, text)
                self._last_regard_day = day_now
            f = F.form_of(b)
            return dict(state=self._state(), delay_s=round(f["delay_s"], 1),
                        words_hint=int(round(f["words"])),
                        proactive=bool(f["proactive"]),
                        u=round(b.u, 3))

    def absence(self, minutes: float, peer: str = None):
        with self.lock:
            minutes = max(0.0, float(minutes))
            before = dict(meals=self.sim.stats["meals"],
                          socials=self.sim.stats["socials"],
                          threats=self.sim.stats["threats"],
                          sick=self.sim.stats["sick"],
                          missed=self.sim.stats.get("missed_windows", 0))
            self.sim.run(stop=self.sim.t + int(minutes * P.SIM_MIN_PER_REAL_MIN))
            persist.save(self.sim, self.path)
            gap = dict(days_alone=round(minutes / P.MIN_PER_DAY, 3),
                       meals=self.sim.stats["meals"] - before["meals"],
                       socials=self.sim.stats["socials"] - before["socials"],
                       threats=self.sim.stats["threats"] - before["threats"],
                       sick_minutes=self.sim.stats["sick"] - before["sick"],
                       missed_windows=self.sim.stats.get("missed_windows", 0) - before["missed"])
            return dict(settlement=settlement.text_for(gap),
                        disclosure=claims.DISCLOSURE,
                        days=gap["days_alone"], state=self._state())


def make_handler(body: Body):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _send(self, code, obj):
            data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path == "/health":
                return self._send(200, body.health())
            return self._send(404, {"error": "not found"})

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            try:
                payload = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                return self._send(400, {"error": "bad json"})
            try:
                if self.path == "/form":
                    return self._send(200, body.form(payload.get("text", ""),
                                                     payload.get("peer")))
                if self.path == "/absence":
                    return self._send(200, body.absence(payload.get("minutes", 0),
                                                        payload.get("peer")))
                if self.path == "/reply":
                    return self._send(200, {"ok": True})
            except Exception as e:
                return self._send(500, {"error": str(e)})
            return self._send(404, {"error": "not found"})

    return H


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", default="evidence/p3/body")
    ap.add_argument("--port", type=int, default=3210)
    ap.add_argument("--peer", default="owner")
    args = ap.parse_args(argv)

    b = Body(args.home, args.peer)
    threading.Thread(target=b.tick_loop, daemon=True).start()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(b))
    print("body daemon on 127.0.0.1:%d (home=%s)" % (args.port, args.home))
    srv.serve_forever()


if __name__ == "__main__":
    main()
