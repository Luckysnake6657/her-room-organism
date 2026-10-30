# -*- coding: utf-8 -*-
"""对比：字面重叠 vs 本地向量，在同一批查询上的召回与误召回。"""
import json
import os
import random
import re

from organism import embeddings, notebook, retrieval


def keywords(text, k=3):
    chunks = re.findall(r"[\u4e00-\u9fff]{2,6}", text or "")
    out = []
    for c in chunks:
        n = min(3, len(c))
        out += [c[:n], c[-n:]]
    return list(dict.fromkeys(out))[:k]


def main():
    nb = notebook.Notebook("evidence/p3/cmw_import/notebook.json")
    rng = random.Random(20261028)
    sample = rng.sample(nb.live(), 50)

    hit_o = hit_e = tried = 0
    for e in sample:
        ks = keywords(e["text"])
        if not ks:
            continue
        tried += 1
        q = ks[0]
        o = retrieval.retrieve(nb, q, k=3)
        hit_o += any(x["id"] == e["id"] for _, x in o)
        # 向量：对候选文本算余弦
        texts = [x["text"] for x in nb.live()]
        vec = embeddings.encode([q] + texts)
        qv, tv = vec[0], vec[1:]
        import numpy as np
        sims = np.dot(tv, qv)
        top = np.argsort(-sims)[:3]
        hit_e += any(nb.live()[i]["id"] == e["id"] for i in top)

    neg = retrieval.retrieve(nb, "量子纠缠实验数据")
    texts = [x["text"] for x in nb.live()]
    vec = embeddings.encode(["量子纠缠实验数据"] + texts)
    import numpy as np
    sims = np.dot(vec[1:], vec[0])
    print("queries", tried)
    print("overlap recall", round(hit_o / tried, 3))
    print("embed   recall", round(hit_e / tried, 3))
    print("overlap negative hits", len(neg))
    print("embed   negative top sim", round(float(max(sims)), 3))
    json.dump(dict(tried=tried, overlap=hit_o / tried, embed=hit_e / tried,
                   neg_overlap=len(neg), neg_embed_max=float(max(sims))),
              open("evidence/p3/retrieval_compare.json", "w", encoding="utf-8"))


if __name__ == "__main__":
    main()
