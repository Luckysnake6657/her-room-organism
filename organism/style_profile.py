# -*- coding: utf-8 -*-
"""P0：从她自己的历史统计风格画像（不手写规则）。

数据：evidence/p3/cmw_sessions/her_lines.jsonl（5105 条）
输出：evidence/p3/style_profile.json
"""
import json
import os
import re
import statistics

SRC = "evidence/p3/cmw_sessions/her_lines.jsonl"
OUT = "evidence/p3/style_profile.json"

PUNCT = {"，": "comma", ",": "comma", "。": "period", ".": "period",
         "？": "question", "?": "question", "！": "exclam", "!": "exclam",
         "…": "ellipsis", "~": "tilde", "～": "tilde", "、": "enum",
         "：": "colon", ":": "colon", "；": "semi", ";": "semi"}
PARTICLES = ["嗯", "啊", "吧", "呢", "哦", "呀", "啦", "嘛", "哈", "嘿", "唉", "诶"]
FUNC = ["的", "了", "我", "你", "他", "她", "是", "不", "在", "有", "就", "都",
        "也", "还", "又", "很", "太", "吗", "什么", "怎么", "这", "那", "一下",
        "一个", "然后", "但是", "因为", "所以", "觉得", "知道", "可能"]
EMOJI = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF]")


def pct(xs, p):
    if not xs:
        return 0
    xs = sorted(xs)
    k = int(round((len(xs) - 1) * p))
    return xs[k]


def main():
    texts = []
    for line in open(SRC, encoding="utf-8"):
        d = json.loads(line)
        t = (d.get("text") or "").strip()
        if t:
            texts.append(t)
    lens = [len(t) for t in texts]
    n = len(texts)
    out = dict(n=n,
               length=dict(mean=round(statistics.mean(lens), 2),
                           p10=pct(lens, 0.1), p50=pct(lens, 0.5),
                           p90=pct(lens, 0.9), max=max(lens)),
               short_rate=round(sum(1 for x in lens if x <= 6) / n, 3),
               long_rate=round(sum(1 for x in lens if x >= 30) / n, 3),
               question_rate=round(sum(1 for t in texts if "？" in t or "?" in t) / n, 3),
               emoji_rate=round(sum(1 for t in texts if EMOJI.search(t)) / n, 3))
    total_chars = sum(lens)
    out["punct_per_100"] = {}
    for ch, name in PUNCT.items():
        c = sum(t.count(ch) for t in texts)
        out["punct_per_100"][name] = round(c / total_chars * 100, 2)
    out["particle_per_100"] = {p: round(sum(t.count(p) for t in texts) / total_chars * 100, 2)
                               for p in PARTICLES}
    out["func_per_100"] = {w: round(sum(t.count(w) for t in texts) / total_chars * 100, 2)
                           for w in FUNC}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(json.dumps({k: out[k] for k in ("n", "length", "question_rate",
                                          "emoji_rate", "short_rate")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
