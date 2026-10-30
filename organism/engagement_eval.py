# -*- coding: utf-8 -*-
"""介入定价的分布检查：不要求标签，先看会不会退化成"全 now/全 later"。"""
import json
import re

from organism.engagement import price
from organism.model import Body


def main():
    texts = []
    for line in open("evidence/p3/cmw_messages/messages.jsonl", encoding="utf-8"):
        d = json.loads(line)
        if not d.get("isSelf") and d.get("isOwner"):
            t = re.sub(r"\[[^\]]*\]", "", d.get("text") or "").strip()
            if len(t) >= 4:
                texts.append(t)
    texts = texts[:60]
    b = Body()
    out = [price(b, t)["decision"] for t in texts]
    from collections import Counter
    print("n", len(texts), Counter(out))
    print("strong/weak examples:",
          sum(1 for t in texts if price(b, t)["explicit"] == 1.0),
          sum(1 for t in texts if price(b, t)["explicit"] == 0.5))
    # 状态差时应该更多 later
    b2 = Body()
    b2.a, b2.e = 0.9, 0.2
    out2 = [price(b2, t)["decision"] for t in texts]
    print("bad state", Counter(out2))


if __name__ == "__main__":
    main()
