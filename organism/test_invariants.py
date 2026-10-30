# -*- coding: utf-8 -*-
"""仪器自检：不测科学假设，只测「我们量东西的工具本身没坏」。

HANDOFF 纪律第 1 条：仪器要配已知阳性自检。
这里把最容易被悄悄破坏的几条性质固定成断言：

1. D >= 0，且偏离设定点会让 D 变大
2. 消融开关真的冻结了对应变量
3. 同 seed + 同噪声 → 逐位可重现
4. 化妆消融（dummy）与基线逐位相同
5. 渲染文本里没有数字/单位
6. 饿到极限会死（存活判据真的会触发）

用法：python -m organism.test_invariants
"""
import json
import math
import os
import shutil
import sys
import tempfile
import time

from . import params as P
from . import persist
from . import record as R
from .model import Body, circ_dist_h
from .render import check_no_numbers, render_run
from .sim import Sim

CTX = dict(hour=12.0, asleep=False, active=False, cold=0.0, light=1.0, place=P.HOME)


def check(cond, msg, fails):
    if not cond:
        fails.append(msg)


def main():
    fails = []

    # 1) D 的性质
    b = Body()
    check(b.D() >= 0, "D>=0", fails)
    b.e = 0.05
    check(b.D() > 0.5, "D grows when energy is far from setpoint (%.2f)" % b.D(), fails)
    b2 = Body()
    b2.e = 0.65
    check(b.D() > b2.D(), "low energy has larger D than setpoint energy", fails)

    # 2) 消融冻结
    for key, attr, target in (("energy", "e", "energy"), ("sleep", "s", "sleep"),
                              ("stress", "a", "stress"), ("immune", "i", "immune"),
                              ("lonely", "l", "lonely")):
        bb = Body(lesion=(key,))
        for _ in range(30):
            bb.step(1.0, CTX)
        check(abs(getattr(bb, attr) - P.SP[target]) < 1e-9,
              "lesion_%s freezes %s" % (key, attr), fails)

    # 3) 重现性
    r1 = Sim(5, (), 1005, "allostatic", P.DAYS).run()
    r2 = Sim(5, (), 1005, "allostatic", P.DAYS).run()
    check(r1["features"] == r2["features"], "same seed+noise reproduces bitwise", fails)

    # 4) 化妆消融 == 基线
    r3 = Sim(5, ("dummy",), 1005, "allostatic", P.DAYS).run()
    check(r1["features"] == r3["features"], "cosmetic lesion is bitwise identical", fails)

    # 5) 渲染文本无数字/单位
    text = render_run(r1, 5, 3)
    check(not check_no_numbers(text), "render has no digits/units: %s"
          % check_no_numbers(text)[:3], fails)

    # 6) 饿死
    bh = Body()
    bh.e = 0.01
    for _ in range(P.TERMINAL_MIN["energy"] + 10):
        bh.step(1.0, CTX)
        if bh.dead:
            break
    check(bh.dead and bh.death_cause == "energy", "starvation triggers death", fails)

    # 7) 环上距离
    check(abs(circ_dist_h(23.5, 0.5) - 1.0) < 1e-9, "circular distance wraps", fails)

    # 8) 结构化记录：自检通过，缺口真的被记出来
    rs = Sim(7, (), 1007, "allostatic", P.DAYS).run()
    summ = R.summarize(rs)
    check(not R.validate(summ), "records validate: %s" % R.validate(summ)[:2], fails)
    check(all(d["wake"] is not None or d["sleep"] is not None or d["gaps"]["no_sleep"]
              for d in summ["days"]), "every day has at least one anchor", fails)

    re_ = Sim(7, ("energy",), 1007, "allostatic", P.DAYS).run()
    se = R.summarize(re_)
    check(all(d["gaps"]["no_meal"] for d in se["days"]),
          "energy lesion records no_meal every day", fails)

    rsl = Sim(7, ("sleep",), 1007, "allostatic", P.DAYS).run()
    ssl = R.summarize(rsl)
    check(all(d["gaps"]["no_sleep"] for d in ssl["days"]),
          "sleep lesion records no_sleep every day", fails)

    # 9) 世界信号：每天都有天亮/天黑/来客信号；密集威胁周里能写出"被惊动过"
    for d in summ["days"]:
        kinds = [s["kind"] for s in d["signals"]]
        check("dawn" in kinds and "dusk" in kinds, "day %d has dawn+dusk" % d["day"], fails)
        check(sum(1 for k in kinds if k in ("person_arrives", "person_absent")) == 1,
              "day %d has exactly one person signal" % d["day"], fails)
    dense = render_run(Sim(205, (), 1205, "allostatic", P.DAYS, challenge="dense").run(), 205, 5)
    check("惊动过" in dense, "dense week renders a startle cause", fails)

    # 10) 离线续算：跑一半、落盘、读档、补完 == 一路跑完
    continuous = Sim(21, (), 1021, "allostatic", P.DAYS).run()
    part = Sim(21, (), 1021, "allostatic", P.DAYS)
    part.run(stop=P.T_START_MIN + 2 * P.MIN_PER_DAY + 333)
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    try:
        persist.save(part, path)
        resumed = persist.load(path)
        remaining = (P.T_START_MIN + P.DAYS * P.MIN_PER_DAY) - part.t
        persist.resume(resumed, real_minutes=remaining)
        check(resumed.result()["features"] == continuous["features"],
              "offline catch-up reproduces continuous run", fails)
        check(resumed.last_gap["sim_minutes"] > 0, "gap report counts elapsed time", fails)
    finally:
        os.remove(path)

    # 11) 对外措辞：能说的通过，越界的被抓出来
    from . import claims
    check(claims.check_claims(claims.DISCLOSURE) == [], "disclosure passes claims check", fails)
    check(claims.check_claims("她一直在等你") != [], "forbidden claim is caught", fails)
    check(claims.check_claims(render_run(rs, 7, 3)) == [],
          "rendered log contains no relational claims", fails)

    # 12) 形式通道：底线永远成立，恢复不超过基线
    from . import form
    bad = Body(product=True)
    bad.chronic = dict(energy=3.0, stress=3.0, immune=3.0)
    bad.e, bad.a, bad.i, bad.s, bad.l = 0.30, 0.90, 0.85, 0.80, 0.90
    fb = form.form_of(bad)
    check(fb["responds"] is True, "worst state still responds", fails)
    check(fb["delay_s"] <= P.FORM_DELAY_MAX_S, "delay bounded", fails)
    check(fb["words"] >= P.FORM_WORDS_MIN, "words above floor", fails)
    check(fb["proactive"] is False, "no proactive when chronic", fails)

    good = Body()
    good.e, good.a, good.s, good.l = 0.70, 0.12, 0.25, 0.60
    fg = form.form_of(good)
    check(fg["words"] <= P.FORM_WORDS_MAX and fg["delay_s"] >= P.FORM_DELAY_BASE_S,
          "recovery does not exceed baseline warmth", fails)

    # 13) 结算单：世界主语、无第二人称、无反事实、无阿拉伯数字
    from . import settlement
    text = settlement.text_for(dict(days_alone=4, meals=11, missed_windows=2,
                                    sick_minutes=526))
    check("你" not in text and "如果" not in text, "settlement has no second person", fails)
    check(not any(c.isdigit() for c in text), "settlement has no ascii digits", fails)
    check(claims.check_claims(text) == [], "settlement passes claims", fails)

    # 14) 慢参数：解绑随离线上升、一次接触不能重置、只改表达不改状态
    long_alone = Sim(5, (), 1005, "allostatic", 30, product=True)
    long_alone.run()
    check(0.50 < long_alone.body.u < 0.65,
          "ungrafting rises to ~0.58 after 30 days (half-life 14, %.2f)" % long_alone.body.u, fails)

    a = Body()
    a.e, a.s, a.a, a.i, a.l = 0.45, 0.60, 0.45, 0.20, 0.60
    a.u = 0.0
    b = Body()
    b.e, b.s, b.a, b.i, b.l = 0.45, 0.60, 0.45, 0.20, 0.60
    b.u = 0.70
    fa, fb = form.form_of(a), form.form_of(b)
    check(fb["delay_s"] > fa["delay_s"] and fb["words"] < fa["words"]
          and fb["topic"] == "self", "same state, different history -> different form", fails)
    check(abs(a.D() - b.D()) < 1e-12, "ungrafting does not change the state", fails)

    c = Body()
    c.u = 0.50
    c.tend()
    check(c.u >= 0.48, "one contact does not reset ungrafting", fails)

    # 15) 会话回路：结算只在被问时给；离线一天后结算里出现"独处"
    from . import chat
    import json as _json
    fd, spath = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.remove(spath)
    try:
        s = chat.Session(spath, dry=True)
        check(s.say("你好")["kind"] == "reply", "session replies", fails)
        check("不记得" in s.say("这段时间")["text"], "settlement carries disclosure", fails)
        st = _json.load(open(spath, encoding="utf-8"))
        st["saved_at"] -= 86400
        _json.dump(st, open(spath, "w", encoding="utf-8"), ensure_ascii=False)
        s2 = chat.Session(spath, dry=True)
        check(s2.last_gap and s2.last_gap["days_alone"] >= 0.9,
              "offline day appears in settlement", fails)
    finally:
        if os.path.exists(spath):
            os.remove(spath)

    # 16) 事实一致性：不能和今天的日子打架；不能出现她没有的东西
    from . import consistency
    facts = ["吃过东西", "出过门"]
    check(consistency.check("我没吃饭，一直没出门。", facts) != [],
          "catches food/out contradiction", fails)
    check(consistency.check("今天上班好累。", facts) != [],
          "catches out-of-world job", fails)
    check(consistency.check("今天吃了点东西，也出去过。", facts) == [],
          "passes consistent text", fails)

    # 17) 人物卡：合法、不盖住状态、世界词表按卡放宽、陌生人模式
    from . import brief, persona
    p = persona.PERSONA_V1
    check(p.validate() == [], "persona v1 valid", fails)
    good = Body()
    good.e, good.s, good.a, good.i, good.l = 0.75, 0.25, 0.12, 0.05, 0.15
    bad = Body()
    bad.e, bad.s, bad.a, bad.i, bad.l = 0.32, 0.80, 0.75, 0.65, 0.80
    fg = form.form_of(good, persona=p)
    fb = form.form_of(bad, persona=p)
    check(fg["words"] >= 1.3 * fb["words"], "persona keeps state variation", fails)
    check(consistency.check("今天上班去了", [], p.world_bans()) == [],
          "persona allows its own world", fails)
    check(consistency.check("今天上班去了", []) != [],
          "global bans still catch it without persona", fails)
    stranger = brief.as_prompt(brief.make(good, persona=p, mode="stranger"))
    check("第一次见面" in stranger and "熟人" not in stranger,
          "stranger mode does not assume familiarity", fails)

    # 18) 本子：检索、假前提必须拒、有支撑才许断言、纠正后仍能检索到
    from . import notebook
    nb = notebook.Notebook()
    e = nb.add("你下周三要去医院复查")
    check(nb.retrieve("复查") == [e], "notebook retrieves by keyword", fails)
    txt, replaced = notebook.gate_reply("记得，你说过要辞职。", [], "你记得我说过要辞职吧？")
    check(replaced and txt == notebook.REFUSAL, "fake premise is refused", fails)
    txt, replaced = notebook.gate_reply("你说过你下周三要去医院复查。",
                                        nb.retrieve("复查"), "你记得吗")
    check(not replaced, "supported assertion passes", fails)
    nb.update(e["id"], text="你把复查改到了周五")
    check([x["text"] for x in nb.retrieve("下周")] == ["你把复查改到了周五"],
          "correction keeps old keywords retrievable", fails)
    check(notebook.quote(nb.retrieve("复查")[0]).startswith("你上次说："),
          "quote reads from the notebook", fails)

    # 19) 边界闸 + 疑问句记忆门
    from . import boundary
    _, cut = boundary.check("能试试。", "你能叫我亲爱的吗", "stranger")
    check(cut, "stranger boundary refuses intimacy", fails)
    _, cut2 = boundary.check("能试试。", "你能叫我亲爱的吗", "acquaintance")
    check(not cut2, "acquaintance boundary does not block", fails)
    _, wh_cut = notebook.gate_reply("不知道。", nb.retrieve("复查"),
                                    "我复查是什么时候来着？")
    check(wh_cut, "unsupported answer to a when-question is gated", fails)
    # 已知限制：说错细节但含关键词（"下下周"含"下周"）不会被拦——v0 只做词面支撑。

    # 20) 断网话术：只说一次、不道歉、过禁语
    from . import offline
    n = offline.Notice()
    check(n.fallback() == offline.NOTICE, "offline notice spoken once", fails)
    check(n.fallback() is None, "offline notice not repeated", fails)
    check(n.recover() == offline.RECOVERED, "recovery spoken", fails)
    check(claims.check_claims(offline.NOTICE) == [], "offline notice passes claims", fails)
    check("对不起" not in offline.NOTICE and "抱歉" not in offline.NOTICE,
          "offline notice does not apologise", fails)

    # 21) 嘴的路由：API 挂了要退回本地，并标记 offline
    from . import api_client, mouth as _mouth
    old_chat, old_local = api_client.chat, _mouth._local_raw
    old_avail = api_client.available
    api_client.available = lambda: True
    api_client.chat = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down"))
    _mouth._local_raw = lambda *a, **k: "我在。"
    try:
        raw, used_api, offline_flag = _mouth._raw("s", "u", 32, 0.8)
        check(raw == "我在。" and used_api is False and offline_flag is True,
              "api failure falls back to local and flags offline", fails)
    finally:
        api_client.chat, _mouth._local_raw = old_chat, old_local
        api_client.available = old_avail

    # 22) 数据边界：导出不含 key、删除可验证、告知说清发送与删除
    from . import privacy
    fd1, p1 = tempfile.mkstemp(suffix=".json")
    os.close(fd1)
    fd2, p2 = tempfile.mkstemp(suffix=".json")
    os.close(fd2)
    try:
        with open(p1, "w", encoding="utf-8") as f:
            _json.dump({"t": 1}, f)
        with open(p2, "w", encoding="utf-8") as f:
            _json.dump({"entries": [{"text": "你怕黑"}]}, f)
        bundle = privacy.export(p1, p2)
        check("api_key" not in _json.dumps(bundle, ensure_ascii=False),
              "export excludes api key", fails)
        r = privacy.delete(p1, p2)
        check(r["ok"] and not os.path.exists(p1), "delete removes and verifies", fails)
        d = privacy.disclosure()
        check("发送" in d and "删除" in d, "disclosure covers sending and deletion", fails)
    finally:
        for p in (p1, p2):
            if os.path.exists(p):
                os.remove(p)

    # 23) 契约测试 50 场景全过
    from . import contract_tests
    cases = contract_tests.build()
    check(len(cases) == 50, "contract suite has 50 cases", fails)
    bad_cases = [c for c in cases if not contract_tests.check_case(c)]
    check(not bad_cases, "all 50 contract cases pass", fails)

    # 24) 延迟排队：到点才释放
    fd3, qpath = tempfile.mkstemp(suffix=".json")
    os.close(fd3)
    os.remove(qpath)
    try:
        from . import chat as _chat
        q = _chat.Session(qpath, dry=True)
        r = q.ask("你好", now=0)
        check(q.poll(now=0.1) is None, "queued reply is not released early", fails)
        check(q.poll(now=r["delay_s"] + 1) is not None,
              "queued reply released after its delay", fails)
    finally:
        if os.path.exists(qpath):
            os.remove(qpath)

    # 25) 态度（regard）：同状态不同历史 -> 形式不同；能涨能掉；不越界
    from . import relation
    lo = Body()
    lo.e, lo.s, lo.a, lo.i, lo.l = 0.60, 0.40, 0.30, 0.10, 0.40
    lo.regard = 0.15
    hi = Body()
    hi.e, hi.s, hi.a, hi.i, hi.l = 0.60, 0.40, 0.30, 0.10, 0.40
    hi.regard = 0.85
    flo, fhi = form.form_of(lo), form.form_of(hi)
    check(fhi["words"] >= 1.15 * flo["words"],
          "regard changes expression without changing state", fails)
    check(relation.stance(lo) != relation.stance(hi), "regard changes stance", fails)
    check(claims.check_claims(relation.stance(lo)) == [],
          "low regard stance carries no guilt talk", fails)
    mid = Body()
    relation.update(mid, "随便吧")
    check(mid.regard < 0.5, "dismissive lowers regard", fails)
    relation.update(mid, "你今天累不累")
    check(mid.regard > 0.47, "responsive raises regard", fails)
    for _ in range(100):
        relation.update(mid, "随便")
    check(mid.regard >= 0.0, "regard is clamped", fails)

    # 26) 性格漂移：有界、双向、同状态可辨
    from . import drift
    up = Body()
    down = Body()
    for _ in range(30):
        drift.weekly(up, 0.02)
        drift.weekly(down, -0.02)
    check(abs(up.trait_drift) <= 0.15 + 1e-9 and abs(down.trait_drift) <= 0.15 + 1e-9,
          "trait drift is bounded", fails)
    check(up.trait_drift > 0 > down.trait_drift, "trait drift goes both ways", fails)
    pup = Body()
    pup.e, pup.s, pup.a, pup.i, pup.l = 0.60, 0.40, 0.30, 0.10, 0.40
    pup.trait_drift = 0.15
    pdn = Body()
    pdn.e, pdn.s, pdn.a, pdn.i, pdn.l = 0.60, 0.40, 0.30, 0.10, 0.40
    pdn.trait_drift = -0.15
    fup = form.form_of(pup, persona=persona.PERSONA_V1)
    fdn = form.form_of(pdn, persona=persona.PERSONA_V1)
    check(fup["words"] >= 1.20 * fdn["words"],
          "personality drift is visible at the same state", fails)

    # 27) 校准：分箱均值降 ECE，覆盖率接近阈值，宽度可报
    from . import calib
    import random as _random
    rng = _random.Random(1)
    synth = []
    for _ in range(300):
        c = rng.random()
        y = 1 if rng.random() < c else 0
        synth.append((c ** 0.5, y))       # 原始置信被高估
    cal, val = synth[:150], synth[150:]
    table = calib.bin_means(cal)
    check(calib.ece(val, table) < calib.ece(val),
          "calibration lowers ece", fails)
    check(calib.coverage(val, table, 0.70) >= 0.60,
          "calibrated coverage is not below threshold", fails)
    check(calib.width(table) > 0 and calib.wis(val, table) >= 0,
          "width and wis are reportable", fails)

    # 28) 习惯 + 30 天纵向：两臂要分开
    from . import habits, longitudinal
    nb3 = notebook.Notebook()
    for t in ("你下周三要去医院复查", "你把复查改到了周五", "复查结果还没出来"):
        nb3.add(t)
    hb = habits.detect(nb3)
    check(hb and hb[0]["topic"] == "复查", "habit detection finds repeated topic", fails)
    check(habits.detect(notebook.Notebook()) == [], "no habits from empty notebook", fails)
    warm = longitudinal.run("warm", 10)
    cold = longitudinal.run("cold", 10)
    check(warm[-1]["regard"] > cold[-1]["regard"],
          "warm history raises regard", fails)
    check(warm[-1]["words"] > cold[-1]["words"],
          "warm history keeps her talking more", fails)

    # 29) 依恋三要素：只对你、跨时间、有让渡
    from . import attachment as _att
    bb = Body()
    bb.regard = 0.80
    before = _att.relation_snapshot(bb)
    check(_att.npc_contact(bb, 10) == before,
          "npc contact does not move the relationship state", fails)
    hi = Body()
    hi.regard, hi.u = 0.80, 0.20
    lo = Body()
    lo.regard, lo.u = 0.20, 0.20
    check(_att.willing(hi, 0.8) and not _att.willing(lo, 0.8),
          "cost: high regard accepts a tired bid, low regard declines", fails)
    check(_att.willing(hi, 0.0), "rested she accepts regardless", fails)

    # 30) 连续性：关系状态跨存档保住（regard / 漂移 / U）
    from . import persist as _persist
    fd4, cpath = tempfile.mkstemp(suffix=".json")
    os.close(fd4)
    os.remove(cpath)
    try:
        from .sim import Sim as _Sim
        s30 = _Sim(3, (), 1003, "allostatic", 7)
        s30.run(stop=360 + 240)
        s30.body.regard = 0.82
        s30.body.trait_drift = 0.11
        s30.body.u = 0.33
        _persist.save(s30, cpath)
        c30 = _persist.load(cpath)
        check(abs(c30.body.regard - 0.82) < 1e-9
              and abs(c30.body.trait_drift - 0.11) < 1e-9
              and abs(c30.body.u - 0.33) < 1e-9,
              "relationship state survives save/load", fails)
    finally:
        if os.path.exists(cpath):
            os.remove(cpath)

    # 31) 入口：说一句带"医院"的话 -> 先问、说"对"才入本；聊天能引用
    import io as _io
    import contextlib as _ctx
    from unittest import mock as _mock
    from . import app as _app
    ahome = os.path.join("evidence", "p3", "_app_test")
    os.makedirs(ahome, exist_ok=True)
    try:
        lines = ["你好", "我下周三要去医院复查", "对", "我养了一只猫叫团子", "/exit"]
        buf = _io.StringIO()
        with _mock.patch("builtins.input", side_effect=lines), \
                _ctx.redirect_stdout(buf):
            _app.main(["--home", ahome, "--dry"])
        nb4 = notebook.Notebook(os.path.join(ahome, "notebook.json"))
        texts = [e["text"] for e in nb4.live()]
        check(any("医院" in t and "复查" in t for t in texts),
              "app proposes and confirms a high-risk fact", fails)
        check(any("猫" in t for t in texts), "app auto-records a low-risk fact", fails)
    finally:
        import shutil as _shutil
        _shutil.rmtree(ahome, ignore_errors=True)

    # 32) 记忆五层：工作/检索/巩固/遗忘/元记忆
    import datetime as _dt
    from . import (working, retrieval, consolidate as _cons, forget as _forget,
                   metamemory as _meta)
    w = []
    for i in range(10):
        working.add(w, "user" if i % 2 == 0 else "her", "第%d句" % i, i)
    check(len(w) == working.MAXLEN, "working memory keeps only 7 turns", fails)
    check(working.prompt_lines(w)[-1].endswith("第9句"), "working memory keeps the latest", fails)

    nbm = notebook.Notebook()
    nb_old = nbm.add("你怕黑")
    nb_new = nbm.add("你下周三要去医院复查")
    scored = retrieval.retrieve(nbm, "复查")
    check(scored and scored[0][1]["id"] == nb_new["id"], "retrieval prefers the relevant entry", fails)
    check(_meta.tier_of(scored) == "strong", "relevant+recent scores strong", fails)
    check(_meta.tier_from_score(0.5) == "fuzzy" and _meta.tier_from_score(0.1) == "none",
          "metamemory tiers map correctly", fails)

    nbc = notebook.Notebook()
    for i, t in enumerate(("你下周三要去医院复查", "你把复查改到了周五", "复查结果还没出来")):
        e = nbc.add(t, type="event")
        e["created_at"] = (_dt.datetime.now() - _dt.timedelta(days=2 - i)).strftime(
            "%Y-%m-%dT%H:%M:%S")
    cands = _cons.candidates(nbc)
    check(bool(cands), "consolidation finds a repeated topic", fails)
    check(cands[0]["text"] in [e["text"] for e in nbc.live()],
          "consolidated text is verbatim, never invented", fails)
    made = _cons.apply(nbc, cands[0])
    check(made is not None and made["status"] == "pending",
          "consolidation proposes a pending entry", fails)
    check(_cons.apply(nbc, cands[0]) is None, "consolidation does not duplicate", fails)

    now = _dt.datetime.now()
    e = nbc.live()[0]
    e["last_access"] = (now - _dt.timedelta(days=120)).strftime("%Y-%m-%dT%H:%M:%S")
    e["strength"] = 1.0
    check(_forget.state(e, now) == "faded", "unused memory fades", fails)
    _forget.touch(e, now)
    check(_forget.touch(e, now) is not None, "access refreshes strength", fails)

    # 元记忆：模糊档不许说成确定
    br_f = brief.make(Body(), memory_tier="fuzzy")
    out_f = _mouth._postprocess("本子上写着：你下周三去医院复查。", br_f,
                                "我周几复查来着？", False)
    check(out_f["text"].startswith("我好像记得"), "fuzzy tier rewrites certainty", fails)

    # 会话：跨轮进工作记忆，并存档
    fd5, spath5 = tempfile.mkstemp(suffix=".json")
    os.close(fd5)
    os.remove(spath5)
    try:
        sq = _chat.Session(spath5, dry=True)
        sq.say("我下周三要去医院复查")
        sq.say("那我周几去来着？")
        check(len(sq.sim.body.working) == 4, "session keeps working-memory turns", fails)
    finally:
        if os.path.exists(spath5):
            os.remove(spath5)

    # 33) 身体守护进程：实时/补算/form/absence/存档
    from . import daemon as _daemon
    import shutil as _shutil2
    dhome = os.path.join("evidence", "p3", "_daemon_test")
    _shutil2.rmtree(dhome, ignore_errors=True)
    try:
        bd = _daemon.Body(dhome)
        h0 = bd.health()
        check(set(("t", "state", "D", "u")) <= set(h0), "daemon health has state", fails)
        f0 = bd.form("今天怎么样")
        check(8.0 <= f0["delay_s"] <= 300.0, "daemon form delay is bounded", fails)
        a = bd.absence(4320)          # 三天
        check(a["days"] == 3.0 and "独处" in a["settlement"],
              "daemon absence settles in world terms", fails)
        check("不记得" in a["disclosure"], "absence carries disclosure", fails)
        check(bd.sim.body.u > 0.0, "ungrafting rises while apart", fails)
        t_before = bd.sim.t
        bd2 = _daemon.Body(dhome)     # 重载 + 挂钟补算
        check(bd2.sim.t >= t_before, "daemon persists and catches up", fails)
    finally:
        _shutil2.rmtree(dhome, ignore_errors=True)

    # 34) 意图层 + 器官：move 只看状态，器官不决定说什么
    from . import intent as _intent, organ as _organ
    b_stress = Body()
    b_stress.a = 0.80
    check(_intent.decide(b_stress)["move"] == "brief", "stress shortens the move", fails)
    b_cold = Body()
    b_cold.regard = 0.20
    check(_intent.decide(b_cold)["move"] == "guarded", "low regard guards the move", fails)
    b_lone = Body()
    b_lone.l = 0.80
    check(_intent.decide(b_lone, proactive_ok=True)["move"] == "initiate",
          "loneliness can initiate", fails)
    check(_intent.decide(Body(), asked_memory=True)["move"] == "refuse",
          "asking about unremembered facts refuses", fails)
    br34 = brief.make(b_stress)
    adj34 = _intent.form_adjust(_intent.decide(b_stress), br34)
    check(adj34["words"] < br34["words"], "intent adjusts form, not identity", fails)
    check(_organ.render({"move": "refuse"}, br34)["text"] == notebook.REFUSAL,
          "organ renders refusal without a model", fails)

    # 35) 记忆抽取：原子性 + 可逆（反复压缩不丢条目）
    from . import memorize as _mem
    check(_mem.extract("我喜欢逃课，我周三要去医院复查") ==
          ["我喜欢逃课", "我周三要去医院复查"], "extracts atomic facts", fails)
    check(_mem.extract("我今天有点累") == [], "transient states are not facts", fails)
    check(_mem.extract("他说我喜欢猫") == [], "third-person is not her fact", fails)
    check(_mem.extract("我喜欢猫吗？") == [], "questions are not facts", fails)
    long = "10/28 他说了一堆关于架构的话，我们聊到很晚，然后我就说我不懂"
    check(all(len(x) <= 30 for x in _mem.extract(long)), "no paragraph-sized entries", fails)

    fdnb, fpath = tempfile.mkstemp(suffix=".json")
    os.close(fdnb)
    try:
        with open(fpath, "w", encoding="utf-8") as f:
            f.write('{"next": 1, "entries": []}')
        nb35 = notebook.Notebook(fpath)
        for t in ("我下周三复查", "我对猫毛过敏", "我答应给他带书"):
            nb35.add(t, type="fact")
        texts = [e["text"] for e in nb35.live()]
        for _ in range(10):
            _forget.sweep(nb35)
        check([e["text"] for e in nb35.live()] == texts,
              "repeated compaction keeps every entry (reversible)", fails)
    finally:
        for p in (fpath + ".bak", fpath):
            if os.path.exists(p):
                os.remove(p)

    # 36) 连续性：常驻 tick 会推进；离线两天后重载能认出"离开过"
    from . import native as _native
    nbase = os.path.join("evidence", "p3", "_native_test")
    shutil.rmtree(nbase, ignore_errors=True)
    try:
        os.makedirs(os.path.join(nbase, "imp"))
        with open(os.path.join(nbase, "imp", "persona.json"), "w", encoding="utf-8") as f:
            json.dump({"card": "你是她。", "name": "她", "words_base": 13}, f, ensure_ascii=False)
        with open(os.path.join(nbase, "imp", "notebook.json"), "w", encoding="utf-8") as f:
            f.write('{"next": 1, "entries": []}')
        n = _native.Native(os.path.join(nbase, "data"), os.path.join(nbase, "imp"), tick=False)
        t0 = n.sim.t
        n._last = time.monotonic() - 300 * 60
        n._advance()
        check(n.sim.t >= t0 + 300, "resident tick advances the body", fails)
        n.close()
        spath = os.path.join(nbase, "data", "session.json")
        with open(spath, encoding="utf-8") as f:
            st = json.load(f)
        st["saved_at"] = time.time() - 2 * 86400
        with open(spath, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False)
        n2 = _native.Native(os.path.join(nbase, "data"), os.path.join(nbase, "imp"), tick=False)
        check(n2.pending_gap is not None and n2.pending_gap.get("long") is True,
              "two days offline is recognised as a long gap", fails)
        n2._last_contact = 0
        n2.sim.body.l = 0.9
        n2.sim.body.regard = 0.9
        check(n2.maybe_proactive(quiet_hours=3) is True, "lonely and quiet can initiate", fails)
        p1 = n2.take_proactive(dry=True)
        check(p1 is not None and p1.get("proactive") is True, "initiative becomes one message", fails)
        check(n2.take_proactive(dry=True) is None, "initiative fires once, not twice", fails)
        n2._last_contact = time.time()
        check(n2.maybe_proactive(quiet_hours=3) is False, "recent contact blocks initiative", fails)
        n2.close()
    finally:
        shutil.rmtree(nbase, ignore_errors=True)

    # 38) 群记忆只读、情绪底色、印象只进语气不进事实
    from . import import_bridge as _ib, legacy as _legacy
    st38 = {"conversations": {
        "group:1": {"activeTopics": [{"text": "群里聊了猫", "lastMentionAt": 0}]},
        "private:owner": {"emotion": {"pad": [0.5, 0.5, 0.0]}}}}
    g38 = _ib.group_topics(st38)
    check(len(g38) == 1 and g38[0].get("scope") == "group:1",
          "group memories are imported read-only", fails)
    m38 = _ib.mood_payload(st38)
    check("心情不错" in m38["text"], "mood comes from pad", fails)
    br38 = brief.make(Body())
    br38["persona"] = _legacy.LegacyPersona("你是她。")
    br38["mood"] = "有点低落"
    br38["impressions"] = ["他嘴硬"]
    p38 = _legacy.prompt(br38, "在吗")
    check("底色" in p38 and "印象" in p38, "mood and impressions reach the prompt", fails)

    # 39) 校准：用户纠正足够多次后，写死的置信会被拉低，检索不再用它
    fd39, p39 = tempfile.mkstemp(suffix=".json")
    os.close(fd39)
    try:
        with open(p39, "w", encoding="utf-8") as f:
            f.write('{"next": 1, "entries": []}')
        nb39 = notebook.Notebook(p39)
        e39 = nb39.add("我下周三复查", confidence=0.9)
        for _ in range(10):
            nb39.record_outcome(e39, False)
        check(e39.get("calibrated") == 0.0, "wrong recalls lower calibrated confidence", fails)
        check(len(retrieval.retrieve(nb39, "复查")) == 0,
              "unreliable memory is not retrieved", fails)
        nb39b = notebook.Notebook(p39)
        check(len(nb39b.outcomes) == 10, "calibration outcomes persist", fails)
    finally:
        for p in (p39 + ".bak", p39):
            if os.path.exists(p):
                os.remove(p)

    # 40) 确认流：pending 只有被确认/删掉才会离开
    fd40, p40 = tempfile.mkstemp(suffix=".json")
    os.close(fd40)
    try:
        with open(p40, "w", encoding="utf-8") as f:
            f.write('{"next": 1, "entries": []}')
        nb40 = notebook.Notebook(p40)
        e40 = nb40.propose("我周三复查")
        check(e40["status"] == "pending", "proposals start pending", fails)
        check(len([e for e in nb40.live() if e["status"] == "pending"]) == 1,
              "pending is visible", fails)
        nb40.confirm(e40["id"])
        check(e40["status"] == "confirmed", "confirm turns it into memory", fails)
        e40b = nb40.propose("我讨厌香菜")
        nb40.delete(e40b["id"])
        check(all(e["id"] != e40b["id"] for e in nb40.live()), "reject removes it", fails)
    finally:
        for p in (p40 + ".bak", p40):
            if os.path.exists(p):
                os.remove(p)

    # 41) 影子模式：只读她的私聊，只写草稿，不发送
    wbase = os.path.join("evidence", "p3", "_watch_test")
    shutil.rmtree(wbase, ignore_errors=True)
    try:
        os.makedirs(os.path.join(wbase, "imp"))
        with open(os.path.join(wbase, "imp", "persona.json"), "w", encoding="utf-8") as f:
            json.dump({"card": "你是她。", "name": "她", "words_base": 13}, f, ensure_ascii=False)
        with open(os.path.join(wbase, "imp", "notebook.json"), "w", encoding="utf-8") as f:
            f.write('{"next": 1, "entries": []}')
        with open(os.path.join(wbase, "state.json"), "w", encoding="utf-8") as f:
            json.dump({"conversations": {"private:owner": {"recentMessages": [
                {"isSelf": False, "text": "在吗", "time": 1000}]}}}, f, ensure_ascii=False)
        nw = _native.Native(os.path.join(wbase, "data"), os.path.join(wbase, "imp"), tick=False)
        nw.watch(os.path.join(wbase, "state.json"), draft=False, once=True)
        drafts = os.path.join(wbase, "data", "drafts.jsonl")
        check(os.path.exists(drafts) and "在吗" in open(drafts, encoding="utf-8").read(),
              "shadow writes drafts without sending", fails)
        watch_state = json.load(open(os.path.join(wbase, "data", "watch.json"), encoding="utf-8"))
        check(watch_state.get("last") == 1000, "shadow remembers where it stopped", fails)
        check(nw.respond(["没事", "嗯"], dry=True) is None,
              "pure acknowledgements can go unanswered", fails)
        check(nw.respond(["在吗"], dry=True) is not None,
              "a real message still gets a reply", fails)
        nw.close()
    finally:
        shutil.rmtree(wbase, ignore_errors=True)

    # 42) 成长回路对照：开成长会写日记/抽候选，关成长不会
    gbase = os.path.join("evidence", "p3", "_grow_test")
    shutil.rmtree(gbase, ignore_errors=True)
    try:
        os.makedirs(os.path.join(gbase, "imp"))
        with open(os.path.join(gbase, "imp", "persona.json"), "w", encoding="utf-8") as f:
            json.dump({"card": "你是她。", "name": "她", "words_base": 13}, f, ensure_ascii=False)
        with open(os.path.join(gbase, "imp", "notebook.json"), "w", encoding="utf-8") as f:
            f.write('{"next": 1, "entries": []}')
        ng = _native.Native(os.path.join(gbase, "g"), os.path.join(gbase, "imp"),
                            tick=False, grow=True)
        check(os.path.exists(os.path.join(gbase, "g", "diary.md")), "growth writes diary", fails)
        ng.say("我喜欢逃课", dry=True)
        check(any(e["status"] == "pending" for e in ng.nb.live()),
              "growth writes back new facts", fails)
        ng.close()
        nn = _native.Native(os.path.join(gbase, "n"), os.path.join(gbase, "imp"),
                            tick=False, grow=False)
        check(not os.path.exists(os.path.join(gbase, "n", "diary.md")),
              "growth can be switched off", fails)
        nn.close()
    finally:
        shutil.rmtree(gbase, ignore_errors=True)

    # 43) 成长必须是非线性的：阶跃/饱和/递减/指数
    from . import growth_eval as _ge
    check(_ge.run()["ok"], "growth is nonlinear (step/saturating/exponential)", fails)

    # 44) 混合主动：默认过日子；明确请求才办事；状态差就 defer
    check(_intent.decide_mode(Body(), "在吗") == "life", "default is life mode", fails)
    check(_intent.decide_mode(Body(), "帮我看看这个报错") == "task",
          "explicit request enters task mode", fails)
    b44 = Body()
    b44.a = 0.9
    check(_intent.decide_mode(b44, "帮我看看这个报错") == "defer",
          "bad state defers the task", fails)

    # 45) 介入定价：不是分类，是按状态决定 now/brief/later
    from . import engagement as _eng
    check(_eng.price(Body(), "帮我看看这个报错")["decision"] == "now",
          "clear request is engaged now", fails)
    check(_eng.price(Body(), "今天好累")["decision"] == "brief",
          "small talk gets a brief reply", fails)
    b45 = Body()
    b45.a, b45.e = 0.9, 0.2
    check(_eng.price(b45, "帮我看看这个报错")["decision"] in ("brief", "later"),
          "bad state does not engage fully", fails)
    check(_eng.price(b45, "在吗")["decision"] == "later",
          "bad state can defer small talk", fails)

    # 46) Stub 测试床：同 seed 同哈希，换 seed 变哈希
    from . import stub as _stub
    check(_stub.run(7, 30)["hash"] == _stub.run(7, 30)["hash"],
          "stub mouth is deterministic for the same seed", fails)
    check(_stub.run(7, 30)["hash"] != _stub.run(8, 30)["hash"],
          "stub mouth changes with the seed", fails)

    # 47) 校准必须按条目：纠正假记忆不能压掉同置信的真记忆
    import json as _json
    import os as _os
    import tempfile as _tf
    from . import notebook as _nb
    _d = _tf.mkdtemp()
    _p = _os.path.join(_d, "nb.json")
    _json.dump({"next": 1, "entries": []}, open(_p, "w", encoding="utf-8"))
    _n = _nb.Notebook(_p)
    _true = _n.add("他对花生过敏。", type="fact", confidence=0.95)
    _false = _n.add("他对花生不过敏。", type="fact", confidence=0.95)
    for _i in range(10):
        _n.record_outcome(_false, False)
    check(_false["calibrated"] == 0 and _true["calibrated"] == 0.95,
          "per-entry calibration must not suppress true memories", fails)

    # 48) 重排只排序：说"无"时必须回退字面 top1，而不是丢掉
    from . import rerank as _rk
    _d2 = _tf.mkdtemp()
    _p2 = _os.path.join(_d2, "nb.json")
    _json.dump({"next": 1, "entries": []}, open(_p2, "w", encoding="utf-8"))
    _n2 = _nb.Notebook(_p2)
    _n2.add("他喜欢无糖乌龙茶。", type="fact", confidence=0.9)
    _n2.add("他养了一只猫。", type="fact", confidence=0.9)
    _old = _rk._llm_pick
    try:
        _rk._llm_pick = lambda q, t: []
        check(len(_rk.retrieve(_n2, "无糖乌龙茶", fallback=True)) == 1,
              "rerank falls back to literal top1 when it says none", fails)
        _rk._llm_pick = lambda q, t: [0]
        check(len(_rk.retrieve(_n2, "无糖乌龙茶", fallback=True)) == 1,
              "rerank returns its pick when it has one", fails)
    finally:
        _rk._llm_pick = _old

    # 49) 置信分层：高分为断言、中分为对冲、低分/空为弃权
    from . import memory_policy as _mp
    check(_mp.band([(0.9, {"calibrated": 0.9})]) == "assert", "high score asserts", fails)
    check(_mp.band([(0.25, {"calibrated": 0.8})]) == "hedge", "mid score hedges", fails)
    check(_mp.band([(0.1, {})]) == "none", "low score abstains", fails)
    check(_mp.band([]) == "none", "empty retrieval abstains", fails)

    # 50) 查询改写与原子化
    from . import query_rewrite as _qr
    check("你还记得" not in _qr.rewrite("你还记得我上次说要去医院复查吗")["query"],
          "rewrite strips filler", fails)
    check("复查" in _qr.rewrite("你还记得我上次说要去医院复查吗")["query"],
          "rewrite keeps key term", fails)
    from . import atomic as _at
    check(_at.is_atomic("下周三要去医院复查心脏。"), "atomic fact detected", fails)
    check(not _at.is_atomic("哈哈哈哈"), "small talk is not atomic", fails)

    # 51) 纠正一次后永不断言
    import json as _j2
    import os as _o2
    import tempfile as _t2
    _d3 = _t2.mkdtemp()
    _p3 = _o2.path.join(_d3, "nb.json")
    _j2.dump({"next": 1, "entries": []}, open(_p3, "w", encoding="utf-8"))
    _n3 = _nb.Notebook(_p3)
    _e3 = _n3.add("他周三要去复查。", type="fact", confidence=0.95)
    _n3.record_outcome(_e3, False)
    check(_e3.get("contested") is True, "one correction marks the entry contested", fails)
    check(_mp.band([(0.9, _e3)]) != "assert",
          "contested memory is never asserted again", fails)

    # 52) 前两名分差太小时改对冲
    check(_mp.band([(0.60, {}), (0.58, {})]) == "hedge",
          "close top-2 margin hedges", fails)
    check(_mp.band([(0.60, {}), (0.40, {})]) == "assert",
          "clear top-1 asserts", fails)

    # 53) 分流：寒暄不查记忆，记忆问句要查
    from . import memory_router as _mr
    check(not _mr.should_retrieve("在吗"), "greeting skips memory", fails)
    check(not _mr.should_retrieve("嗯嗯"), "ack skips memory", fails)
    check(_mr.should_retrieve("你还记得我上次说的医院吗"), "memory question retrieves", fails)

    # 54) 单个低分候选：当"提到"而不是"答案"，改对冲
    check(_mp.band([(0.45, {})]) == "hedge", "lone low-score candidate hedges", fails)
    check(_mp.band([(0.60, {})]) == "assert", "lone high-score candidate asserts", fails)

    # 55) 感知层：内感受阈值 + 在场感（含毫秒时间戳）
    from . import perception as _pc
    _b = Body()
    _b.e, _b.load, _b.a, _b.i, _b.s, _b.l = 0.2, 0.2, 0.9, 0.9, 0.9, 0.9
    check("有点累" in _pc.interoception(_b), "low energy is felt", fails)
    check("有点饿" in _pc.interoception(_b), "low load is felt", fails)
    check(len(_pc.interoception(Body())) <= 2, "interoception capped at two", fails)
    import time as _time
    _now = _time.time()
    check(_pc.presence(int(_now * 1000), _now) == "他在", "recent ms ts means present", fails)
    check(_pc.presence(int((_now - 7 * 3600) * 1000), _now) == "他有一阵没来了",
          "old ms ts means absent", fails)
    check(_pc.presence(None) == "", "no ts means no claim", fails)

    # 56) 世界：键鼠在场、声音、天气
    from . import world as _wd
    check(_wd.classify_idle(10) == "他在电脑前", "recent input means present", fails)
    check(_wd.classify_idle(700) == "他离开了一会儿", "long idle means away", fails)
    check(_wd.classify_idle(300) == "", "middle idle says nothing", fails)
    check(_wd.classify_rms(0.5) == "有声音", "loud mic means sound", fails)
    check(_wd.classify_rms(0.0001) == "", "quiet mic says nothing", fails)
    check(_wd.code_to_text(0) == "晴", "weather code maps", fails)

    # 57) 框架模式提示词：意图 + 样例 + 风格约束，且不超过 3 条原话
    from . import framework_persona as _fp
    _r = _fp.build("还行", ["他的手机是华为 P70。"], Body(), "我用的是什么手机")
    check(_r["mode"] == "framework", "framework mode is marked", fails)
    check("【她想】" in _r["prompt"], "intent is in prompt", fails)
    check("【习惯】" in _r["prompt"], "style constraint is in prompt", fails)
    check(len(_r["exemplars"]) <= 3, "at most three exemplars", fails)

    # 58) 框架提示词必须带边界（不编记忆/不暴露提示词）
    check("【边界】" in _r["prompt"], "boundaries are in prompt", fails)
    check("不编记忆" in _r["prompt"], "memory honesty boundary", fails)

    # 59) 感受推断：第一人称、可模糊、不编原因
    from . import affect as _af
    _b1 = Body(); _b1.e, _b1.l, _b1.a, _b1.s, _b1.i = 0.2, 0.7, 0.2, 0.1, 0.0
    _a1 = _af.infer(_b1, "累", "他在")
    check(_a1["label"] in _af.LABELS, "affect label from her vocabulary", fails)
    check(_a1["no_cause"], "affect never fabricates causes", fails)
    check(_a1["confidence"] < 0.7 and "说" in _a1["phrase"],
          "low confidence hedges", fails)
    _b2 = Body(); _b2.e, _b2.l, _b2.a, _b2.s, _b2.i = 0.9, 0.0, 0.0, 0.0, 0.0
    _a2 = _af.infer(_b2, "", "")
    check(_a2["valence"] > 0.6, "healthy body has positive valence", fails)
    check("说" not in _a2["phrase"], "neutral feeling is not hedged as unclear", fails)
    check(_af._phrase("平静", 0.8, "") == "",
          "calm is never announced as a feeling word", fails)

    # 60) 表达层：第一人称、不编原因、低置信不替她下结论
    from . import expression as _ex
    _line = _ex.render(_a1)
    check(_line.startswith("我现在"), "expression is first person", fails)
    check("因为" not in _line and "都是你" not in _line,
          "expression has no fabricated cause", fails)
    _low = _ex.render(dict(phrase="有点累", want="想安静一会儿", confidence=0.3))
    check("想安静" not in _low, "low confidence withholds want", fails)

    # 61) 叙事层：第一人称、只引她自己的话、不编因果
    from . import narrative as _nar
    _n = _nar.build()
    if _n["sources"]:
        check(_n["text"].startswith("这几天我记着"), "narrative is first person", fails)
        check("因为" not in _n["text"], "narrative has no fabricated cause", fails)

    # 62) 短版表达：不超过 12 字、不编原因
    from . import expression_short as _es
    _s = _es.render(_a1)
    check(len(_s) <= 12, "short expression stays short", fails)
    check("因为" not in _s, "short expression has no cause", fails)

    # 63) 披露策略：群里不主动、被问要说、孤独可求回应
    from . import disclosure as _dc
    check(_dc.decide(dict(valence=0.2, arousal=0.7), "在吗", "group")["mode"] == "none",
          "group withholds disclosure", fails)
    check(_dc.decide(dict(valence=0.2, arousal=0.7), "你今天咋样", "owner_private")["mode"]
          in ("brief", "elaborate"), "owner question gets disclosure", fails)
    check(_dc.decide(dict(valence=0.2, arousal=0.6, lonely=0.8), "我在",
                     "owner_private")["mode"] == "seek_response",
          "lonely high intensity seeks response", fails)

    # 64) 复合感受：又累又烦，不只挑一个
    _bm = Body(); _bm.e, _bm.a, _bm.l, _bm.s, _bm.i = 0.3, 0.7, 0.0, 0.0, 0.0
    _am = _af.infer(_bm, "烦", "他在")
    check(len(_am["components"]) >= 2, "mixed feelings keep two components", fails)
    check("又" in _es.render(_am), "mixed feelings are spoken as both", fails)

    # 65) LLM 表达层：披露 none 不报感受；编原因被拦
    from . import expression_llm as _xl
    _orig = _xl.api_client.chat

    def _fake_leak(*a, **k):
        return "我有点累，因为你没回我。"

    _xl.api_client.chat = _fake_leak
    _r_none = _xl.render(_am, "在吗", disclosure={"mode": "none"})
    _r_brief = _xl.render(_am, "你怎么了", disclosure={"mode": "brief"})
    _xl.api_client.chat = _orig
    check(_r_none == "" or "累" not in _r_none, "none disclosure never leaks feelings", fails)
    check("因为" not in _r_brief, "llm expression blocks fabricated cause", fails)

    # 66) 评价融合：所有因素一起算，方向正确
    from . import appraisal as _ap
    _bp = Body(); _bp.l = 0.7
    _out = _ap.fuse(_bp, {"presence": False, "light": 0.5}, "在吗", (), "owner_private", 40)
    _in = _ap.fuse(_bp, {"presence": True, "light": 0.5}, "我回来了", (), "owner_private", 1)
    check(_out["delta_valence"] < 0, "absence lowers valence", fails)
    check(_in["delta_valence"] > 0, "return raises valence", fails)

    # 67) 主动开口：多理由 + 静默时段 + 群聊不主动
    import datetime as _dt
    import time as _tm
    from . import proactive as _pr
    _now = _tm.mktime(_dt.datetime.now().replace(hour=15, minute=0, second=0,
                                                 microsecond=0).timetuple())
    _night = _tm.mktime(_dt.datetime.now().replace(hour=2, minute=0, second=0,
                                                   microsecond=0).timetuple())
    _pb = Body(); _pb.l = 0.7; _pb.e = 0.9
    check(_pr.decide(_pb, _now, 600, False, {"presence": True})["speak"] is True,
          "daytime with reasons speaks", fails)
    check(_pr.decide(_pb, _night, 600, False, {"presence": True})["speak"] is False,
          "0-6 quiet hours never speaks", fails)
    check(_pr.decide(_pb, _now, 600, False, {"presence": True},
                     relation="group")["speak"] is False,
          "group never initiates", fails)

    # 68) 用户模型：24 小时概率、范围合法
    from . import usermodel as _um
    _m = _um.fit([(_tm.time(), "你好"), (_tm.time(), "在吗")])
    check(_m is not None and len(_m["hour_prob"]) == 24, "user model has 24 hours", fails)
    _p = _um.active_prob(_m)
    check(0.0 < _p < 1.0, "active probability in range", fails)

    # 69) 关系修复：冷淡/指正/高严重度
    from . import repair as _rp
    check(_rp.detect(["嗯", "哦", "算了"])["rupture"] is True,
          "cold short replies count as rupture", fails)
    check(_rp.detect(["今天挺好", "晚安"])["rupture"] is False,
          "normal chat is not rupture", fails)
    _hi = _rp.detect(["你错了", "算了", "不想说"])
    check(_hi["rupture"] is True and _hi["action"] in ("apologize", "space"),
          "high severity picks repair action", fails)

    # 70) 学习闭环：周漂移上限、方向、边界
    import os as _os
    import tempfile as _tf
    from . import learning as _lg
    _d = _tf.mkdtemp()
    _p = _os.path.join(_d, "l.json")
    _log = _os.path.join(_d, "l.jsonl")
    for _ in range(10):
        _lg.update("initiative", 1.0, path=_p, log_path=_log)
    _v = _lg.params(_p)["initiative"]
    check(abs(_v - 0.50) <= 0.0201, "weekly drift capped at 0.02", fails)
    _lg.update("initiative", -1.0, path=_p, log_path=_log)
    check(abs(_lg.params(_p)["initiative"] - _v) < 1e-9,
          "no further drift after cap", fails)
    check(sum(1 for _ in open(_log, encoding="utf-8")) >= 10,
          "learning is auditable", fails)

    # 71) 结果记录：主动接受/无视、修复成功/失败
    from . import outcomes as _oc
    check(_oc.proactive_outcome(100, 160) == "accepted", "quick reply counts accepted", fails)
    check(_oc.proactive_outcome(100, 100 + 7 * 3600) == "ignored",
          "late reply counts ignored", fails)
    check(_oc.repair_outcome(True, False, 1) == "repaired", "recovery counts repaired", fails)
    check(_oc.repair_outcome(True, True, 3) == "failed", "persistent rupture fails", fails)

    if fails:
        print("FAIL (%d)" % len(fails))
        for f in fails:
            print("  -", f)
        return 1
    print("PASS: 71 groups of invariants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
