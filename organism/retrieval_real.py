# -*- coding: utf-8 -*-
"""检索的真实问法（改写）评测：不再用关键词片段。

用模型把本子里的条目改写成自然问句，再测 Recall@5 / MRR；
另加 10 条"本子没有"的问题，测误召回。
仍然不是公开语料，但比自造关键词更接近真实分布。
"""
import json
import random
import re

from organism import api_client, notebook, retrieval

PROMPT = """把下面每条事实改写成一句自然的提问（中文，口语），保留关键实体，不要加新信息。
只输出 JSON 数组，顺序对应，例如 ["我什么时候复查？", ...]。
事实：
"""


def rewrite(texts):
    out = []
    for start in range(0, len(texts), 10):
        chunk = texts[start:start + 10]
        body = "\n".join("%d. %s" % (i + 1, t) for i, t in enumerate(chunk))
        arr = None
        for _ in range(3):
            try:
                raw = api_client.chat(PROMPT, body, max_tokens=2500, temperature=0.0)
            except Exception:
                continue
            m = re.search(r"\[.*\]", raw, re.S)
            if not m:
                continue
            try:
                arr = json.loads(m.group(0))
                break
            except Exception:
                continue
        if not arr:
            out.extend([""] * len(chunk))
            continue
        out.extend([str(x) for x in arr][:len(chunk)] + [""] * max(0, len(chunk) - len(arr)))
    return out


ONE = """把这条事实改成一句自然的中文口语提问，只输出问题本身。事实："""


def rewrite_one(text):
    for _ in range(3):
        try:
            raw = api_client.chat(ONE, text, max_tokens=200, temperature=0.0)
        except Exception:
            continue
        q = (raw.strip().splitlines() or [""])[0].strip(' "“”')
        if q:
            return q
    return "关于「%s」，我记得什么？" % text[:10]


def rewrite_robust(texts):
    qs = rewrite(texts)
    return [q if q and q.strip() else "关于「%s」，我记得什么？" % t[:10]
            for t, q in zip(texts, qs)]


def main():
    nb = notebook.Notebook("evidence/p3/cmw_import/notebook.json")
    rng = random.Random(20261029)
    sample = rng.sample(nb.live(), 20)
    qs = rewrite([e["text"] for e in sample])
    hit5, rr = 0, 0.0
    n = 0
    for e, q in zip(sample, qs):
        hits = retrieval.retrieve(nb, q, k=5)
        ids = [x["id"] for _, x in hits]
        n += 1
        if e["id"] in ids:
            hit5 += 1
            rr += 1.0 / (ids.index(e["id"]) + 1)
    neg_qs = ["我上周是不是说过要去看极光", "我的猫叫什么名字", "我什么时候说要换工作",
              "我对花生过敏吗", "我上次体检是哪天", "我借给谁钱了",
              "我的车停在哪", "我答应过谁什么", "我生日是哪天", "我在哪家公司上班"]
    neg_hits = sum(1 for q in neg_qs if retrieval.retrieve(nb, q, k=3))
    out = dict(n=n, recall5=round(hit5 / n, 3) if n else 0,
               mrr=round(rr / n, 3) if n else 0,
               neg_hits=neg_hits, neg_total=len(neg_qs),
               queries=qs)
    json.dump(out, open("evidence/p3/retrieval_real.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps({k: out[k] for k in ("n", "recall5", "mrr", "neg_hits", "neg_total")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
