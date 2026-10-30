# -*- coding: utf-8 -*-
"""反讽/玩梗分类器测试（只输出序号，避免编码问题）。"""
import json

from . import api_client

P = """这句话是不是在玩梗/反讽/说反话/开玩笑？只输出 yes 或 no。

话：%s"""


def main():
    items = json.load(open("evidence/p3/bdi_quiz_data.json", encoding="utf-8"))
    idxs = []
    for i, it in enumerate(items, 1):
        try:
            raw = api_client.chat(P % it["msg"], "", max_tokens=400,
                                  temperature=0.0).strip().lower()
        except Exception:
            raw = ""
        if raw.startswith("yes") or raw.startswith("是"):
            idxs.append(i)
    print("flagged", len(idxs), "/", len(items), "idx", idxs)
    json.dump(idxs, open("evidence/p3/joke_flags.json", "w", encoding="utf-8"))


if __name__ == "__main__":
    main()
