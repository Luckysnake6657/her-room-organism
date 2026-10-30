# -*- coding: utf-8 -*-
"""判读者位置偏差：把同一对 A/B 顺序对调再判一次。

若顺序无关，对调后的胜负应与原判一致（映射回来）；
若不一致，说明存在位置偏差，影子的胜负要打折。
"""
import json

from . import api_client
from .rerank_shadow import JUDGE, show

SRC = "evidence/p3/rerank_fallback.jsonl"
OUT = "evidence/p3/judge_order.jsonl"


def main(n=60):
    rows = [json.loads(l) for l in open(SRC, encoding="utf-8")][:n]
    agree = swap_a = 0
    pairs = []
    for r in rows:
        if not r["lit"] and not r["final"]:
            continue
        # 对调：把 final 放 A，lit 放 B
        try:
            raw = api_client.chat(JUDGE % (r["q"], show(r["final"]), show(r["lit"])), "",
                                  max_tokens=800, temperature=0.0).strip().lower()
        except Exception:
            raw = "tie"
        sw = "b" if raw.startswith("a") else ("a" if raw.startswith("b") else "tie")
        ok = sw == r["judge"]
        agree += ok
        pairs.append(dict(q=r["q"], orig=r["judge"], swapped=sw, agree=ok))
        with open(OUT, "a", encoding="utf-8") as f:
            f.write(json.dumps(pairs[-1], ensure_ascii=False) + "\n")
    print("n", len(pairs), "agree", agree, "rate", round(agree / max(1, len(pairs)), 3))


if __name__ == "__main__":
    main()
