# -*- coding: utf-8 -*-
"""native 的 HTTP 服务：给桥接提供"她现在的状态/处境/记忆"。

    python -m organism.service --data evidence/p3/cmw_native --port 3210

接口：
    GET  /health
    POST /context {text} -> {state, delay_s, words, proactive, mood, bdi, memories, tier}
"""
import argparse
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import brief as B, form as F, metamemory, retrieval
from .native import Native


class Service:
    def __init__(self, data: str, import_dir: str, port: int,
                 state: str = os.environ.get("QQ_STATE", "state/social-v2.json"),
                 rerank: bool = False, rewrite: bool = False,
                 calib: bool = False, world: bool = False,
                 sound: bool = True, persona_shadow: bool = False,
                 affect_shadow: bool = False, affect_llm: bool = False,
                 repair: bool = False, fast: bool = True):
        self.n = Native(data, import_dir)
        self.port = port
        self.state = state
        self.rerank = rerank
        self.rewrite = rewrite
        self.world = world
        self.sound = sound
        self.persona_shadow = persona_shadow
        self.affect_shadow = affect_shadow
        self.affect_llm = affect_llm
        self.repair = repair
        self.fast = fast
        self._affect_cache = {}
        self._bdi_cache = {}
        self._sensors = {}
        self._last_seen = 0.0
        self._pending_proactive = 0.0
        self._repair_active = False
        self._repair_turns = 0
        self.calib = None
        if calib:
            try:
                from .calibrator import Calibrator
                self.calib = Calibrator()
            except Exception:
                self.calib = None
        self._social_mtime = 0.0
        self._last_incoming = 0.0
        try:
            from . import usermodel as _um
            self._umodel = _um.load() or _um.fit_from_state()
        except Exception:
            self._umodel = None
        self.lock = threading.Lock()
        threading.Thread(target=self._ingest_loop, daemon=True).start()

    def _presence_ts(self):
        """读 social-v2 的 lastIncomingAt，带 mtime 缓存。"""
        try:
            m = os.path.getmtime(self.state)
            if m != self._social_mtime:
                with open(self.state, encoding="utf-8") as f:
                    st = json.load(f)
                conv = st.get("conversations", {}).get(
            next((k for k in st.get("conversations", {}) if k.startswith("private:")), ""), {})
                self._last_incoming = float(conv.get("lastIncomingAt") or 0)
                self._social_mtime = m
        except Exception:
            pass
        return self._last_incoming

    def _ingest_loop(self):
        """把真实对话吃进记忆；不生成、不发送。"""
        while True:
            try:
                self.n.watch_ingest(self.state, once=True)
            except Exception:
                pass
            time.sleep(20)

    def proactive(self) -> dict:
        with self.lock:
            b = self.n.sim.body
            now = time.time()
            last = float(self._last_incoming or 0)
            if last > 1e12:
                last /= 1000.0
            gap = ((now - last) / 60.0) if last else 999.0
            sens = self._sensors if (self._sensors and now - float(self._sensors.get("t") or 0) < 15) else None
            from . import proactive as _pr
            from . import usermodel as _um
            _um_ap = _um.active_prob
            ua = None
            try:
                if self._umodel:
                    ua = round(_um_ap(self._umodel, now), 3)
            except Exception:
                ua = None
            busy_now = bool(ua is not None and ua < 0.12)   # 他大概不在，别打扰
            d = _pr.decide(b, now, gap, False, sens, "owner_private", busy=busy_now)
            d["user_active"] = ua
            try:
                with open("evidence/p3/proactive_log.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps(dict(t=now, gap_min=round(gap, 1), **d),
                                       ensure_ascii=False) + "\n")
            except Exception:
                pass
            if not d["speak"]:
                return {}
            out = self.n.take_proactive(dry=False)
            if not out:
                return {}
            self._pending_proactive = now
            return dict(text=out["text"], delay_s=out.get("delay_s", 0),
                        reasons=d.get("reasons"), score=d.get("score"))

    def perceive(self, d: dict) -> dict:
        """传感器读数（摄像头在场感/光线）。只存数值，不存画面。"""
        self._sensors = dict(presence=bool(d.get("presence")),
                             light=float(d.get("light") or 0.0),
                             t=time.time())
        if self._sensors["presence"]:
            self._last_seen = time.time()
        return dict(ok=True)

    def context(self, text: str) -> dict:
        with self.lock:
            now0 = time.time()
            if self._pending_proactive and text:
                from . import outcomes as _oc
                _oc.log("proactive",
                        outcome=_oc.proactive_outcome(self._pending_proactive, now0),
                        latency_s=round(now0 - self._pending_proactive, 1))
                self._pending_proactive = 0.0
            b = self.n.sim.body
            settle = ""
            gap = getattr(self.n, "pending_gap", None)
            if gap:
                try:
                    from . import settlement
                    settle = settlement.text_for(gap) or ""
                except Exception:
                    settle = ""
                self.n.pending_gap = None
            qt = text
            if self.rewrite and text:
                from . import query_rewrite as _qr
                qt = _qr.rewrite(text)["query"]
            from . import memory_router as _mr
            mem_skip = False
            if text and not _mr.should_retrieve(text):
                qt = ""
                mem_skip = True
            if self.rerank and qt and not self.fast:
                from . import rerank as _rr
                scored = _rr.retrieve(self.n.nb, qt, k=3)
                try:
                    lit = [e["text"] for _, e in
                           retrieval.retrieve(self.n.nb, qt, k=3)]
                    with open("evidence/p3/rerank_live.jsonl", "a", encoding="utf-8") as f:
                        f.write(json.dumps(dict(t=time.time(), text=text, literal=lit,
                                                rerank=[e["text"] for _, e in scored]),
                                           ensure_ascii=False) + "\n")
                except Exception:
                    pass
            else:
                scored = retrieval.retrieve(self.n.nb, qt) if qt else []
            if not scored and self.rewrite and text and qt != text:
                # 扩展没命中：回退原句再试一次
                if self.rerank and not self.fast:
                    from . import rerank as _rr
                    scored = _rr.retrieve(self.n.nb, text, k=3)
                else:
                    scored = retrieval.retrieve(self.n.nb, text)
            from .memory_policy import band as _mband
            mb = _mband(scored) if text else "none"
            p_cal = None
            if self.calib is not None and text:
                try:
                    p_cal = round(float(self.calib.p(scored, text)), 3)
                except Exception:
                    p_cal = None
            try:
                with open("evidence/p3/memory_decisions.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps(dict(t=time.time(), text=text, band=mb,
                                            n=len(scored),
                                            top=(round(scored[0][0], 3) if scored else None),
                                            p_cal=p_cal),
                                       ensure_ascii=False) + "\n")
            except Exception:
                pass
            tier = metamemory.tier_of(scored)
            memories = [e["text"] for _, e in scored[:5]] if tier in ("strong", "fuzzy") else []
            bdi = {}
            if text:
                from . import bdi as _bdi
                if self.fast:
                    bdi = self._bdi_cache.get("bdi") or {}

                    def _bdi_bg(t=text):
                        try:
                            r = _bdi.extract(t)
                            if r:
                                self._bdi_cache["bdi"] = r
                        except Exception:
                            pass

                    threading.Thread(target=_bdi_bg, daemon=True).start()
                else:
                    try:
                        bdi = _bdi.extract(text)
                    except Exception:
                        bdi = {}
            f = F.form_of(b, persona=self.n.persona)
            from . import engagement as _eng
            eng = _eng.price(b, text)
            state = B.state_phrase(b) + ("（办事）" if eng["decision"] == "now" else "")
            from . import perception as _pc
            per = _pc.signals(b, self._presence_ts())
            parts = per["intero"] + ([per["presence"]] if per["presence"] else [])
            if self.world:
                try:
                    from . import world as _wd
                    wp = _wd.signals(with_sound=self.sound)[:2]
                    # 键鼠显示人在电脑前时，"他有一阵没来了"（QQ）不成立
                    if "他在电脑前" in wp:
                        parts = [p for p in parts if p != "他有一阵没来了"]
                    parts = parts + wp
                except Exception:
                    pass
            # 摄像头在场感：只用来"确认在"，不用来报"没人"（键鼠负责离开）
            try:
                s = getattr(self, "_sensors", {}) or {}
                if s and time.time() - float(s.get("t") or 0) < 15:
                    if s.get("presence"):
                        parts = [p for p in parts if p != "他有一阵没来了"]
                        if "他在电脑前" not in parts:
                            parts.append("他坐在电脑前")
                    if float(s.get("light") or 1) < 0.12:
                        parts.append("屋里很暗")
            except Exception:
                pass
            if parts:
                state = state + "（" + "；".join(parts) + "）"
            if settle:
                state = settle + "；" + state
            if mb == "hedge":
                state = state + "（记忆不太确定；可以反问确认）"
            elif mb == "none" and text and not mem_skip:
                state = state + "（记忆里没有；别拿相关的事当答案，可以问一句）"
            memo = dict(state=state, delay_s=round(f["delay_s"], 1),
                        words=int(round(f["words"])), proactive=bool(f["proactive"]),
                        mood=self.n.mood, bdi=bdi, memories=memories,
                        tier=tier, u=round(b.u, 3), decision=eng["decision"])
            if self.persona_shadow and text:
                try:
                    from . import framework_persona as _fp
                    memo["persona"] = _fp.build(state, memories, b, text)
                except Exception:
                    pass
            if self.affect_shadow:
                try:
                    from . import affect as _af, expression as _ex, disclosure as _dc, appraisal as _ap
                    _sens = self._sensors if (self._sensors and time.time() - float(self._sensors.get("t") or 0) < 15) else None
                    _away = ((time.time() - self._last_seen) / 60.0) if self._last_seen else 0.0
                    _appr = _ap.fuse(b, _sens, text, memories, "owner_private", _away)
                    _a = _af.infer(b, text, per.get("presence", ""), memories,
                                   valence_shift=_appr["delta_valence"],
                                   extra_components=_appr["extra_components"])
                    _a["appraisal"] = _appr
                    _a["disclosure"] = _dc.decide(_a, text, "owner_private")
                    _akey = ("|".join(_a.get("components") or []), _a["disclosure"]["mode"])
                    if self.affect_llm and _a["disclosure"]["mode"] != "none":
                        cached = self._affect_cache.get("text") if self._affect_cache.get("key") == _akey else ""
                        if cached:
                            _a["text"] = cached
                        else:
                            _a["text"] = _ex.render(_a)   # 本轮先用模板，不阻塞

                            def _bg(aff=_a, key=_akey, ctx=text):
                                try:
                                    from . import expression_llm as _xl
                                    t = _xl.render(aff, ctx, "owner_private", aff["disclosure"])
                                    if t:
                                        self._affect_cache.update(key=key, text=t)
                                except Exception:
                                    pass

                            threading.Thread(target=_bg, daemon=True).start()
                    else:
                        _a["text"] = _ex.render(_a)
                    memo["affect"] = _a
                    try:
                        from . import narrative as _nar
                        memo["self_narrative"] = _nar.build()["text"]
                    except Exception:
                        pass
                except Exception:
                    pass
            if self.repair:
                try:
                    from . import repair as _rp
                    conv = json.load(open(self.state, encoding="utf-8"))
                    ms = []
                    for k, v in (conv.get("conversations") or {}).items():
                        if k.startswith("private:"):
                            ms = v.get("recentMessages") or []
                            break
                    own = [m.get("text") or "" for m in ms if m.get("isOwner") and not m.get("isSelf")][-5:]
                    _r = _rp.detect(own, gap_min=0.0)
                    memo["repair"] = _r
                    try:
                        from . import learning as _lg, outcomes as _oc
                        _prev = getattr(self, "_last_repair", None) or {}
                        if _prev.get("rupture") and not _r.get("rupture"):
                            _oc.log("repair", outcome="repaired", turns=self._repair_turns)
                            _lg.update("expressiveness", 0.5, reason="修复成功")
                            self._repair_turns = 0
                        elif _prev.get("rupture") and _r.get("rupture"):
                            self._repair_turns += 1
                            if self._repair_turns >= 3:
                                _oc.log("repair", outcome="failed", turns=self._repair_turns)
                            _lg.update("expressiveness", -0.3, reason="仍未修复")
                        elif _r.get("rupture") and not _prev.get("rupture"):
                            self._repair_turns = 0
                            _oc.log("repair", outcome="pending", turns=0)
                        self._last_repair = _r
                    except Exception:
                        pass
                except Exception:
                    pass
            return memo


def handler(svc: Service):
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
                return self._send(200, dict(ok=True, t=svc.n.sim.t,
                                            state=svc.n._state() if hasattr(svc.n, "_state") else ""))
            if self.path == "/metrics":
                from . import outcomes as _oc
                return self._send(200, _oc.summary())
            return self._send(404, dict(error="not found"))

        def do_POST(self):
            n = int(self.headers.get("Content-Length", 0))
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
            except Exception:
                return self._send(400, dict(error="bad json"))
            if self.path == "/perceive":
                return self._send(200, svc.perceive(body))
            if self.path == "/context":
                try:
                    return self._send(200, svc.context(str(body.get("text") or "")))
                except Exception as e:
                    return self._send(500, dict(error=str(e)))
            if self.path == "/proactive":
                try:
                    return self._send(200, svc.proactive())
                except Exception as e:
                    return self._send(500, dict(error=str(e)))
            return self._send(404, dict(error="not found"))

    return H


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="evidence/p3/cmw_native")
    ap.add_argument("--import-dir", default="evidence/p3/cmw_import")
    ap.add_argument("--port", type=int, default=3210)
    ap.add_argument("--state", default=os.environ.get("QQ_STATE", "state/social-v2.json"))
    ap.add_argument("--rerank", action="store_true")
    ap.add_argument("--rewrite", action="store_true")
    ap.add_argument("--calib", action="store_true")
    ap.add_argument("--world", action="store_true")
    ap.add_argument("--persona-shadow", action="store_true")
    ap.add_argument("--affect", action="store_true")
    ap.add_argument("--affect-llm", action="store_true")
    ap.add_argument("--slow", action="store_true")
    ap.add_argument("--repair", action="store_true")
    ap.add_argument("--no-sound", action="store_true")
    args = ap.parse_args(argv)
    svc = Service(args.data, args.import_dir, args.port, args.state, args.rerank,
                  args.rewrite, args.calib, args.world, not args.no_sound,
                  args.persona_shadow, args.affect, args.affect_llm,
                  args.repair, fast=not args.slow)
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), handler(svc))
    print("native service on 127.0.0.1:%d" % args.port)
    srv.serve_forever()


if __name__ == "__main__":
    main()
