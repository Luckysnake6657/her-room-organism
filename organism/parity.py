# -*- coding: utf-8 -*-
"""记忆平行测试：源数据 vs 导入后的本子。

三件事：
1. 完整性：源里的每一条话题/日记，导入后是否**逐字**还在
2. 可检索：抽 50 条，用其中的关键词查，看它是否进 top3
3. 不编造：问本子上没有的事，是否一条都不返回（应该走"没记"）
"""
import argparse
import json
import random
import re

from . import import_bridge, notebook, retrieval


def norm(s: str) -> str:
    return re.sub(r"\s+", "", str(s or ""))


def keywords(text: str, k: int = 3) -> list:
    """从正文里取 2–3 字的中文片段当查询词（不做分词，够用）。"""
    chunks = re.findall(r"[\u4e00-\u9fff]{2,6}", text)
    if not chunks:
        return []
    out = []
    for c in chunks:
        n = min(3, len(c))
        out.append(c[:n])
        out.append(c[-n:])
    return list(dict.fromkeys(out))[:k]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", default=r"D:\qq-bridge\state\social-v2.json")
    ap.add_argument("--import-dir", default="evidence/p3/cmw_import")
    ap.add_argument("--sample", type=int, default=50)
    ap.add_argument("--seed", type=int, default=20261028)
    args = ap.parse_args(argv)

    src = import_bridge.build(args.state, import_bridge.DEFAULT_ROLE,
                              import_bridge.DEFAULT_DIARY)
    src_texts = [norm(e["text"][:200]) for e in src["notebook"]]
    nb = notebook.Notebook(args.import_dir + "/notebook.json")
    got = [norm(e["text"]) for e in nb.live()]

    missing = [t for t in src_texts if t not in got]
    extra = [t for t in got if t not in src_texts]
    print("完整性：源 %d 条 / 导入 %d 条 / 缺 %d / 多 %d" % (
        len(src_texts), len(got), len(missing), len(extra)))
    if missing:
        print("  缺的前两条：", [m[:20] for m in missing[:2]])

    rng = random.Random(args.seed)
    sample = rng.sample(nb.live(), min(args.sample, len(nb.live())))
    hit, tried = 0, 0
    for e in sample:
        ks = keywords(e["text"])
        if not ks:
            continue
        tried += 1
        found = False
        for q in ks:
            hits = retrieval.retrieve(nb, q, k=3)
            if any(norm(x["text"]) == norm(e["text"]) for _, x in hits):
                found = True
                break
        hit += 1 if found else 0
    print("可检索：%d/%d = %.2f" % (hit, tried, hit / max(1, tried)))

    neg = retrieval.retrieve(nb, "量子纠缠实验数据")
    from . import metamemory
    neg_tier = metamemory.tier_of(neg)
    print("不编造：未知查询命中 %d 条 / 档位 %s（应为 none）" % (len(neg), neg_tier))

    ok = (not missing) and (hit / max(1, tried) >= 0.90) and neg_tier == "none"
    print("PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
