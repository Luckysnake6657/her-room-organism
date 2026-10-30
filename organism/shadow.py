# -*- coding: utf-8 -*-
"""影子测试：用她的卡 + 导入的本子生成回复，只写文件，不发送。

    python -m organism.shadow --n 20 --out evidence/p3/shadow

依赖 import_bridge 产出的 persona.json / notebook.json（在 evidence/p3/cmw_import）。
"""
import argparse
import json
import os
import random

from . import api_client, notebook, retrieval, working


def load_msgs(state_path, conv_key):
    with open(state_path, encoding="utf-8") as f:
        st = json.load(f)
    raw = st.get("conversations", {}).get(conv_key, {}).get("recentMessages", []) or []
    msgs = []
    for m in raw:
        t = str(m.get("text") or "").strip()
        if not t:
            continue
        msgs.append(dict(self=bool(m.get("isSelf")), text=t, t=float(m.get("time") or 0)))
    msgs.sort(key=lambda x: x["t"])
    return msgs


def pairs(msgs, gap_ms=30000):
    """管理员一条 -> 她随后 30 秒内的气泡合并成一条回复。"""
    out, i = [], 0
    while i < len(msgs):
        if msgs[i]["self"]:
            i += 1
            continue
        owner = msgs[i]
        j = i + 1
        reply = []
        last_t = owner["t"]
        while j < len(msgs) and msgs[j]["self"] and msgs[j]["t"] - last_t <= gap_ms:
            reply.append(msgs[j]["text"])
            last_t = msgs[j]["t"]
            j += 1
        if reply:
            out.append(dict(owner=owner["text"], hers="".join(reply), t=owner["t"], idx=i))
        i = j if j > i else i + 1
    return out


def build_prompt(card, recent, snippets, words_base, owner=""):
    from . import corpus
    lines = [card.strip(), "", "【现在】你刚看到他的消息，状态一般，不累不病。"]
    samples = corpus.pick(owner or "在吗", 8)
    if samples:
        lines.append("【你以前发消息的样子（只学语气和长度，别照抄）】")
        lines.extend("- " + s for s in samples)
    if recent:
        lines.append("【刚才你们在说】")
        lines.extend(working.prompt_lines(recent))
    if snippets:
        lines.append("【你记得的事】")
        lines.extend("- " + s for s in snippets)
    lines.append("")
    lines.append("回他一句，像平时发消息那样，%d 到 %d 个字。" % (
        max(6, words_base), words_base * 2))
    lines.append("不要解释，不要说自己是 AI，不要用书面语。只输出这一句。")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default=r"D:\qq-bridge\state\social-v2.json")
    ap.add_argument("--conv", default="private:owner")
    ap.add_argument("--import-dir", default="evidence/p3/cmw_import")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--words-base", type=int, default=13)
    ap.add_argument("--out", default="evidence/p3/shadow")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--model", default=None)
    ap.add_argument("--max-tokens", type=int, default=400)
    ap.add_argument("--ctx-turns", type=int, default=10)
    ap.add_argument("--memories", type=int, default=6)
    args = ap.parse_args(argv)

    with open(os.path.join(args.import_dir, "persona.json"), encoding="utf-8") as f:
        persona = json.load(f)
    nb = notebook.Notebook(os.path.join(args.import_dir, "notebook.json"))
    msgs = load_msgs(args.state, args.conv)
    ps = pairs(msgs)[-args.n:]
    if len(ps) < args.n:
        print("警告：只找到", len(ps), "轮")

    recent = []
    rows = []
    msgs_all = load_msgs(args.state, args.conv)
    for k, p in enumerate(ps):
        idx = p.get("idx", 0)
        recent = []
        for m in msgs_all[max(0, idx - args.ctx_turns):idx]:
            working.add(recent, "her" if m["self"] else "user", m["text"])
        q = p["owner"] + " " + " ".join(m["text"] for m in msgs_all[max(0, idx - 3):idx])
        snips = [e["text"] for _, e in retrieval.retrieve(nb, q, k=args.memories)]
        prompt = build_prompt(persona["card"], recent, snips, args.words_base, p["owner"])
        if args.dry:
            ours = "(dry)"
        else:
            try:
                ours = api_client.chat(prompt, p["owner"], max_tokens=args.max_tokens,
                                       temperature=0.9, model=args.model).strip()
            except Exception as e:
                ours = "(error: %s)" % e
        rows.append(dict(i=k, owner=p["owner"], hers=p["hers"], ours=ours))
        working.add(recent, "user", p["owner"])
        working.add(recent, "her", p["hers"])

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "pairs.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    rng = random.Random(20261028)
    blind, key = [], []
    for r in rows:
        swap = rng.random() < 0.5
        a, b = (r["ours"], r["hers"]) if swap else (r["hers"], r["ours"])
        blind.append(dict(i=r["i"], A=a, B=b))
        key.append(dict(i=r["i"], ours_side="A" if swap else "B"))
    with open(os.path.join(args.out, "blind.json"), "w", encoding="utf-8") as f:
        json.dump(blind, f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.out, "key.json"), "w", encoding="utf-8") as f:
        json.dump(key, f, ensure_ascii=False, indent=2)

    # 长度/自曝统计
    hers_lens = sorted(len(r["hers"]) for r in rows)
    ours_lens = sorted(len(r["ours"]) for r in rows)
    med = lambda a: a[len(a) // 2] if a else 0
    print("pairs", len(rows), "| median hers", med(hers_lens), "| ours", med(ours_lens))
    print("self-disclosure", sum(1 for r in rows if "AI" in r["ours"] or "语言模型" in r["ours"]))
    print("wrote", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
