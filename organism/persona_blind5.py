# -*- coding: utf-8 -*-
"""第五轮：B 加 24 字硬上限，同一批 A 复用，只换 B。"""
import json
import random

from . import renderer_b as R, api_client


def main():
    prof = R.load_profile()
    lines = R.load_lines()
    old = json.load(open("evidence/p3/persona_blind4.json", encoding="utf-8"))
    rng = random.Random(21)
    rows = []
    for r in old:
        a = next(t for lab, t in (r["first"], r["second"]) if lab == "A")
        c = r["context"]
        st = r["state"]
        ex = R.exemplars(c, lines)
        prompt = R.build_prompt(prof, st, [], ex, c, max_chars=24)
        try:
            b = api_client.chat(prompt, c, max_tokens=800, temperature=0.8).strip()
        except Exception:
            b = ""
        if not b:
            continue
        pair = [("A", a), ("B", b)]
        rng.shuffle(pair)
        rows.append(dict(context=c, state=st, first=pair[0], second=pair[1]))
    md = ["# 像不像她：第五轮（B 限 24 字）", ""]
    for i, r in enumerate(rows, 1):
        md.append("%d. 他说：%s（她当时：%s）" % (i, r["context"], r["state"]))
        md.append("   1) %s" % r["first"][1])
        md.append("   2) %s" % r["second"][1])
    md.append("")
    md.append("回复格式：1:1 2:2 … %d:1" % len(rows))
    open("evidence/p3/persona_blind5.md", "w", encoding="utf-8").write("\n".join(md))
    json.dump(rows, open("evidence/p3/persona_blind5.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    bl = [max(len(next(t for l, t in (r["first"], r["second"]) if l == "B")), 0) for r in rows]
    print("rows", len(rows), "B_max", max(bl), "B_mean", round(sum(bl) / len(bl), 1))


if __name__ == "__main__":
    main()
