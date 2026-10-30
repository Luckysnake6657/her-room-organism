# -*- coding: utf-8 -*-
"""对 30 条新样本跑分类器预测。"""
import json

from . import api_client

P = """这句话是不是在玩梗/反讽/说反话/开玩笑？只输出 yes 或 no。

话：%s"""


def main():
    msgs = json.load(open("evidence/p3/joke30_data.json", encoding="utf-8"))
    preds = []
    for m in msgs:
        try:
            raw = api_client.chat(P % m, "", max_tokens=400, temperature=0.0).strip().lower()
        except Exception:
            raw = ""
        preds.append(bool(raw.startswith("yes") or raw.startswith("是")))
    json.dump(preds, open("evidence/p3/joke30_predictions.json", "w", encoding="utf-8"))
    print("yes", sum(preds), "/", len(preds))


if __name__ == "__main__":
    main()
