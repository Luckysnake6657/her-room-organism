# -*- coding: utf-8 -*-
"""从 qq-bridge 的她的数据里，做人格与记忆适配（只读）。

人格分两半：
1. 原文卡（roles/程妙雯.md 之类）——原样带过去，不改一个字
2. 表达参数——从她自己的历史消息**量出来**，不靠猜
   （平均字数、问句率、感叹率、表情率）

记忆分三类：
- 话题（activeTopics / coreMemory.activeTopics）→ 本子条目（可断言）
- 印象（memberImpressions）→ 单独存，**不可断言**（那是她的判断，不是事实）
- 日记（state/her-diary/*.md）→ 情景条目

用法：
    python -m organism.import_bridge --dry
    python -m organism.import_bridge --out evidence/p3/import_report.json
"""
import argparse
import datetime as dt
import json
import os
import re

DEFAULT_STATE = r"D:\qq-bridge\state\social-v2.json"
DEFAULT_ROLE = r"D:\qq-bridge\roles\她.md"
DEFAULT_DIARY = r"D:\qq-bridge\state\her-diary"
CONV = "private:owner"

IMP = {"high": 0.9, "normal": 0.6, "low": 0.4}


def _ts(ms):
    try:
        return dt.datetime.fromtimestamp(float(ms) / 1000.0).strftime("%Y-%m-%dT%H:%M:%S")
    except Exception:
        return dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def measure_style(conv: dict) -> dict:
    msgs = [m for m in (conv.get("recentMessages") or []) if m.get("isSelf")]
    texts = [str(m.get("plain") or m.get("text") or "") for m in msgs]
    texts = [t for t in texts if t.strip()]
    if not texts:
        return dict(n=0, mean_chars=0.0, question_rate=0.0, exclaim_rate=0.0,
                    emoji_rate=0.0, words_mul=1.0)
    n = len(texts)
    mean_chars = sum(len(t) for t in texts) / n
    q = sum(1 for t in texts if "?" in t or "？" in t) / n
    ex = sum(1 for t in texts if "!" in t or "！" in t) / n
    emoji = sum(1 for t in texts if re.search(r"\[[^\]]{1,6}\]", t)) / n
    words_mul = max(0.50, min(1.40, mean_chars / 60.0))
    return dict(n=n, mean_chars=round(mean_chars, 1), question_rate=round(q, 3),
                exclaim_rate=round(ex, 3), emoji_rate=round(emoji, 3),
                words_mul=round(words_mul, 3))


def _entry(text, type_, importance, created, assertable=True, **extra):
    e = dict(type=type_, text=text[:200], source="bridge", created_at=created,
             confidence=0.90, status="confirmed", importance=importance,
             strength=1.0, keywords=text[:200], legacy=True,
             assertable=bool(assertable),
             last_access=dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"))
    e.update(extra)
    return e


def topics(state: dict, conv_key: str):
    out, seen = [], set()
    for src in (state.get("conversations", {}).get(conv_key, {}).get("activeTopics", []),
                state.get("coreMemory", {}).get("activeTopics", []),
                state.get("coreMemory", {}).get("archived", [])):
        for t in (src or []):
            text = str(t.get("text") or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            out.append(_entry(text, "topic", IMP.get(t.get("importance"), 0.6),
                              _ts(t.get("lastMentionAt")),
                              participants=t.get("participants")))
    return out


def impressions(state: dict, conv_key: str):
    imp = state.get("conversations", {}).get(conv_key, {}).get("memberImpressions", {}) or {}
    out = []
    for k, v in imp.items():
        text = str(v.get("text") if isinstance(v, dict) else v).strip()
        if not text:
            continue
        out.append(dict(member=str(k), text=text[:300],
                        created_at=_ts((v or {}).get("at") if isinstance(v, dict) else None)))
    return out


def diary_entries(path: str):
    out = []
    if not os.path.isdir(path):
        return out
    for name in sorted(os.listdir(path)):
        if not name.endswith(".md"):
            continue
        day = name[:-3]
        try:
            with open(os.path.join(path, name), encoding="utf-8") as f:
                lines = f.read().splitlines()
        except Exception:
            continue
        for line in lines:
            s = line.strip()
            if not s or s.startswith("#") or s.startswith("---"):
                continue
            if len(s) < 4 or len(s) > 160:
                continue
            out.append(_entry(s, "event", 0.6, day + "T20:00:00"))
    return out


def group_topics(state: dict):
    """群记忆：只导话题，不导整段聊天（降噪）。只读，不碰群。"""
    out = []
    for key, conv in (state.get("conversations") or {}).items():
        if not str(key).startswith("group:"):
            continue
        for t in (conv.get("activeTopics") or []):
            text = str(t.get("text") or "").strip()
            if not text:
                continue
            out.append(_entry(text, "topic", 0.5, _ts(t.get("lastMentionAt")),
                              scope=key, participants=t.get("participants")))
    return out


def mood_payload(state: dict, conv_key: str = CONV) -> dict:
    """她此刻的情绪底色（pad：愉悦/唤醒/支配）。只给语气，不当事实。"""
    pad = (((state.get("conversations") or {}).get(conv_key) or {})
           .get("emotion") or {}).get("pad") or []
    try:
        p, a = float(pad[0]), float(pad[1])
    except Exception:
        return {"text": ""}
    if p > 0.3:
        mood = "心情不错"
    elif p < -0.3:
        mood = "有点低落"
    else:
        mood = "心里平静"
    if a > 0.3:
        energy = "有精神"
    elif a < -0.3:
        energy = "没什么力气"
    else:
        energy = "不困也不兴奋"
    return {"text": "%s，%s" % (mood, energy), "pad": pad}


def conversation_entries(conv: dict, limit: int = 200):
    """最近对话也进本子：他说过的话当事实，她说过的话当经历。"""
    out = []
    msgs = [m for m in (conv.get("recentMessages") or []) if str(m.get("text") or "").strip()]
    for m in msgs[-limit:]:
        text = str(m.get("text")).strip()
        who = "他说" if not m.get("isSelf") else "我说"
        out.append(_entry("%s：%s" % (who, text), "fact" if not m.get("isSelf") else "event",
                          0.55 if not m.get("isSelf") else 0.45,
                          _ts(m.get("time")),
                          assertable=not m.get("isSelf")))
    return out


def build(state_path, role_path, diary_dir, conv_key=CONV):
    with open(state_path, encoding="utf-8") as f:
        state = json.load(f)
    conv = state.get("conversations", {}).get(conv_key, {})
    card = ""
    if role_path and os.path.exists(role_path):
        with open(role_path, encoding="utf-8") as f:
            card = f.read()
    style = measure_style(conv)
    nb = (topics(state, conv_key) + conversation_entries(conv)
          + group_topics(state) + diary_entries(diary_dir))
    imp = impressions(state, conv_key)
    mood = mood_payload(state, conv_key)
    return dict(
        source=dict(state=state_path, role=role_path, diary=diary_dir, conv=conv_key),
        persona=dict(card=card, card_chars=len(card), style=style),
        notebook=nb, impressions=imp, mood=mood,
        stats=dict(notebook=len(nb), assertable=sum(1 for x in nb if x["assertable"]),
                   impressions=len(imp), diary=len([x for x in nb if x["type"] == "event"]),
                   topics=len([x for x in nb if x["type"] == "topic"]),
                   groups=len([x for x in nb if x.get("scope")])),
    )


def _persona_payload(r, words_base):
    st = r["persona"]["style"]
    return dict(
        id="cmw", version="legacy-1", name="她",
        card=r["persona"]["card"],
        card_chars=r["persona"]["card_chars"],
        style=st,
        words_base=words_base,
        words_mul=1.0,
        delay_mul=1.0,
        note="words_base 由历史消息中位数推的临时值；正式值要用日志里的每轮总字数校准。",
    )


def _notebook_payload(entries):
    out = []
    for i, e in enumerate(entries, start=1):
        d = dict(e)
        d["id"] = i
        out.append(d)
    return dict(next=len(out) + 1, entries=out)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default=DEFAULT_STATE)
    ap.add_argument("--role", default=DEFAULT_ROLE)
    ap.add_argument("--diary", default=DEFAULT_DIARY)
    ap.add_argument("--conv", default=CONV)
    ap.add_argument("--out", default="evidence/p3/import_report.json")
    ap.add_argument("--write-dir", default=None,
                    help="写出 persona.json / notebook.json / impressions.json")
    ap.add_argument("--words-base", type=float, default=24.0)
    ap.add_argument("--dry", action="store_true")
    args = ap.parse_args(argv)

    r = build(args.state, args.role, args.diary, args.conv)
    print("人格卡字符数:", r["persona"]["card_chars"])
    print("表达参数:", r["persona"]["style"])
    print("记忆:", r["stats"])

    if args.write_dir:
        os.makedirs(args.write_dir, exist_ok=True)
        with open(os.path.join(args.write_dir, "persona.json"), "w", encoding="utf-8") as f:
            json.dump(_persona_payload(r, args.words_base), f, ensure_ascii=False, indent=2)
        with open(os.path.join(args.write_dir, "notebook.json"), "w", encoding="utf-8") as f:
            json.dump(_notebook_payload(r["notebook"]), f, ensure_ascii=False, indent=2)
        with open(os.path.join(args.write_dir, "impressions.json"), "w", encoding="utf-8") as f:
            json.dump(r["impressions"], f, ensure_ascii=False, indent=2)
        with open(os.path.join(args.write_dir, "mood.json"), "w", encoding="utf-8") as f:
            json.dump(r["mood"], f, ensure_ascii=False, indent=2)
        with open(os.path.join(args.write_dir, "report.json"), "w", encoding="utf-8") as f:
            json.dump(dict(stats=r["stats"], style=r["persona"]["style"],
                           words_base=args.words_base), f, ensure_ascii=False, indent=2)
        print("wrote", args.write_dir)
        return 0

    if args.dry:
        return 0
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=2)
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
