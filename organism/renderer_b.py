# -*- coding: utf-8 -*-
"""P1：最小提示词渲染器（影子，不发送）。

输入：当前状态 + 相关记忆 + 3 条她自己的原话
输出：一句话；并计算与历史风格分布的 JS 散度。
"""
import json
import math
import re

from . import api_client

PROFILE = "evidence/p3/style_profile.json"
LINES = "evidence/p3/cmw_sessions/her_lines.jsonl"


def load_profile():
    return json.load(open(PROFILE, encoding="utf-8"))


def load_lines():
    out = []
    for line in open(LINES, encoding="utf-8"):
        t = (json.loads(line).get("text") or "").strip()
        if 2 <= len(t) <= 40:
            out.append(t)
    return out


def bigrams(s):
    s = re.sub(r"[\s，。！？、,.!?~～…]+", "", s)
    return {s[i:i + 2] for i in range(len(s) - 1)}


def exemplars(context, lines, k=3):
    cg = bigrams(context)
    scored = []
    for t in lines:
        g = bigrams(t)
        if not g:
            continue
        scored.append((len(cg & g) / len(cg | g), t))
    scored.sort(reverse=True)
    out, seen = [], set()
    for _, t in scored[:200]:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
        if len(out) >= k:
            break
    return out


def build_prompt(profile, state, memories, ex, context="", max_chars=None):
    p50 = profile["length"]["p50"]
    p90 = profile["length"]["p90"]
    ex_text = "\n".join("- %s" % e for e in ex)
    mem = "\n".join("- %s" % m for m in memories[:3])
    cap = ("尽量不超过 %d 字。" % max_chars) if max_chars else ""
    return (
        "先回应【他刚说】的内容，再用她的语气说一句她会说的话。\n"
        "状态只影响语气，不要让状态盖过他说的内容。\n"
        "只输出这句话，不要解释。\n\n"
        "【他刚说】%s\n"
        "【她此刻】%s\n"
        "【相关记忆】\n%s\n"
        "【她以前在这种情况下说过】\n%s\n"
        "【她的说话习惯】中位 %d 字，p90 %d 字；"
        "少用问号（历史 1.4%%）；不用表情（历史 0%%）。%s\n"
        % (context, state, mem or "（无）", ex_text, p50, p90, cap)
    )


def js_divergence(p, q):
    keys = set(p) | set(q)
    eps = 1e-9
    m = {k: (p.get(k, 0) + q.get(k, 0)) / 2 for k in keys}
    def kl(a):
        return sum(a.get(k, 0) * math.log((a.get(k, 0) + eps) / (m[k] + eps))
                   for k in keys if a.get(k, 0) > 0)
    return 0.5 * kl(p) + 0.5 * kl(q)


def length_hist(texts):
    bins = [0, 6, 10, 15, 20, 30, 50, 1000]
    hist = {i: 0 for i in range(len(bins) - 1)}
    for t in texts:
        n = len(t)
        for i in range(len(bins) - 1):
            if bins[i] <= n < bins[i + 1]:
                hist[i] += 1
                break
    total = sum(hist.values()) or 1
    return {i: v / total for i, v in hist.items()}


def main():
    profile = load_profile()
    lines = load_lines()
    msgs = [json.loads(l)["text"] for l in open("evidence/p3/cmw_messages/messages.jsonl", encoding="utf-8")
            if not json.loads(l).get("isSelf") and json.loads(l).get("isOwner")]
    msgs = [m.strip() for m in msgs if 6 <= len(m.strip()) <= 40]
    contexts = msgs[:30]
    outs = []
    for c in contexts:
        ex = exemplars(c, lines)
        prompt = build_prompt(profile, "还行（有点累）", [], ex, c)
        try:
            text = api_client.chat(prompt, c, max_tokens=800, temperature=0.8).strip()
        except Exception as e:
            text = ""
        outs.append(dict(context=c, exemplars=ex, out=text))
    good = [o["out"] for o in outs if o["out"]]
    hist_profile = length_hist([t for t in lines][:5000])
    hist_out = length_hist(good) if good else {}
    out = dict(n=len(outs), generated=len(good), samples=outs,
               js_length=round(js_divergence(hist_profile, hist_out), 3) if good else None,
               out_mean_len=round(sum(len(t) for t in good) / len(good), 1) if good else None,
               out_question_rate=round(sum(1 for t in good if "？" in t) / len(good), 3) if good else None)
    json.dump(out, open("evidence/p3/persona_shadow.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps({k: out[k] for k in ("n", "generated", "js_length",
                                          "out_mean_len", "out_question_rate")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
