# -*- coding: utf-8 -*-
"""样例数消融：k=3 vs k=5，比较风格 JS 与句长。"""
import json

from . import api_client, renderer_b as R


def run(k, n=20):
    prof = R.load_profile()
    lines = R.load_lines()
    msgs = [json.loads(l)["text"] for l in open("evidence/p3/cmw_messages/messages.jsonl", encoding="utf-8")
            if not json.loads(l).get("isSelf") and json.loads(l).get("isOwner")]
    msgs = [m.strip() for m in msgs if 6 <= len(m.strip()) <= 40][:n]
    outs = []
    for c in msgs:
        ex = R.exemplars(c, lines, k=k)
        prompt = (
            "把下面这些『此刻的信息』说成一句她会说的话。\n只输出这句话。\n\n"
            "【她此刻】还行（有点累）\n"
            "【她以前在这种情况下说过】\n%s\n"
            "【她的说话习惯】中位 %d 字，p90 %d 字；问句率 %.1f%%；不用表情。"
            % ("\n".join("- " + e for e in ex), prof["length"]["p50"],
               prof["length"]["p90"], prof["question_rate"] * 100)
        )
        try:
            t = api_client.chat(prompt, c, max_tokens=800, temperature=0.8).strip()
        except Exception:
            t = ""
        if t:
            outs.append(t)
    hist = R.length_hist(lines[:5000])
    js = R.js_divergence(hist, R.length_hist(outs)) if outs else None
    return dict(k=k, n=len(outs), js=round(js, 3) if js is not None else None,
                mean_len=round(sum(len(t) for t in outs) / len(outs), 1) if outs else None,
                samples=outs[:5])


def main():
    out = [run(3), run(5)]
    json.dump(out, open("evidence/p3/persona_ablate.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps([{k: r[k] for k in ("k", "n", "js", "mean_len")} for r in out],
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
