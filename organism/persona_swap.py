# -*- coding: utf-8 -*-
"""换嘴测试：同一套画像/样例，换模型生成，比较风格分布变化。"""
import json

from . import renderer_b as R
from organism import api_client


def main():
    prof = R.load_profile()
    lines = R.load_lines()
    msgs = [json.loads(l)["text"] for l in open("evidence/p3/cmw_messages/messages.jsonl", encoding="utf-8")
            if not json.loads(l).get("isSelf") and json.loads(l).get("isOwner")]
    msgs = [m.strip() for m in msgs if 6 <= len(m.strip()) <= 40]
    outs = []
    for c in msgs[:15]:
        ex = R.exemplars(c, lines)
        prompt = R.build_prompt(prof, "还行（有点累）", [], ex)
        try:
            t = api_client.chat(prompt, c, max_tokens=800, temperature=0.8,
                                model="deepseek-chat").strip()
        except Exception:
            t = ""
        if t:
            outs.append(t)
    hist = R.length_hist(lines[:5000])
    js = R.js_divergence(hist, R.length_hist(outs)) if outs else None
    out = dict(n=len(outs), js_length=round(js, 3) if js is not None else None,
               mean_len=round(sum(len(t) for t in outs) / len(outs), 1) if outs else None)
    json.dump(out, open("evidence/p3/persona_swap.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
