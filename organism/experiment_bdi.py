# -*- coding: utf-8 -*-
"""实验 A：BDI 注入对"像不像她"的影响。

同一串消息，两次生成：
- 基线：现在的 native
- 注入：把 {他在做什么/想要什么/以为什么} 作为事实放进提示词

输出：pairs.jsonl、blind.json/key、extract_review.md（人工核对抽取准确率）。

    python -m organism.experiment_bdi --bursts bursts.json --n 20
    python -m organism.experiment_bdi --state ... --from 1793192539000 --to 1793192601000
"""
import argparse
import json
import os
import random
import shutil

from . import bdi as BDI
from .native import Native


def bursts_from_state(state_path, t0, t1, conv="private:owner", gap_ms=60000):
    s = json.load(open(state_path, encoding="utf-8"))
    msgs = [m for m in s["conversations"][conv].get("recentMessages", [])
            if m.get("text") and t0 <= float(m.get("time") or 0) <= t1]
    msgs.sort(key=lambda m: float(m.get("time") or 0))
    out, cur = [], None
    for m in msgs:
        t = float(m.get("time") or 0)
        if m.get("isSelf"):
            if cur:
                cur["hers"] += str(m.get("text") or "")
            continue
        # 他说的话：只有"还没回、且在窗口内"才并进当前串
        if cur is not None and not cur["hers"] and t - cur["last"] <= gap_ms:
            cur["texts"].append(m["text"])
            cur["last"] = t
        else:
            if cur:
                out.append(cur)
            cur = dict(texts=[m["text"]], hers="", last=t)
    if cur:
        out.append(cur)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--bursts", default=None, help="JSON: [{texts, hers}]")
    ap.add_argument("--state", default=r"D:\qq-bridge\state\social-v2.json")
    ap.add_argument("--from", dest="t0", type=float, default=0)
    ap.add_argument("--to", dest="t1", type=float, default=0)
    ap.add_argument("--base", default="evidence/p3/cmw_native")
    ap.add_argument("--out", default="evidence/p3/bdi_exp")
    ap.add_argument("--force", action="store_true", help="重抽 BDI，不用缓存")
    args = ap.parse_args(argv)

    if args.bursts:
        data = json.load(open(args.bursts, encoding="utf-8"))
    else:
        data = bursts_from_state(args.state, args.t0, args.t1)
    if not data:
        print("没有可用的消息串")
        return 1

    shutil.rmtree(args.out, ignore_errors=True)
    os.makedirs(args.out, exist_ok=True)
    base_dir = os.path.join(args.out, "base")
    bdi_dir = os.path.join(args.out, "bdi")
    shutil.copytree(args.base, base_dir)
    shutil.copytree(args.base, bdi_dir)
    nb = Native(base_dir, "evidence/p3/cmw_import", tick=False)
    nd = Native(bdi_dir, "evidence/p3/cmw_import", tick=False)

    rows, extract = [], []
    texts = ["；".join(b["texts"]) if isinstance(b.get("texts"), list) else str(b["texts"])
             for b in data]
    cache = os.path.join(args.out, "extract.json")
    if os.path.exists(cache) and not args.force:
        extract = json.load(open(cache, encoding="utf-8"))
    else:
        infos = BDI.extract_many(texts, workers=8)
        extract = [dict(i=i, text=t, **info) for i, (t, info) in enumerate(zip(texts, infos))]
    for i, (b, text, e) in enumerate(zip(data, texts, extract)):
        info = {k: e.get(k, "") for k in ("activity", "desire", "belief", "confidence")}
        a = nb.say(text, bdi=None)
        c = nd.say(text, bdi=info)
        rows.append(dict(i=i, owner=text, hers=b.get("hers", ""),
                         base=a["text"], bdi=c["text"]))
        print("[%d] %s\n  基线：%s\n  BDI ：%s" % (i, text[:24], a["text"][:30], c["text"][:30]))

    with open(os.path.join(args.out, "pairs.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(os.path.join(args.out, "extract.json"), "w", encoding="utf-8") as f:
        json.dump(extract, f, ensure_ascii=False, indent=2)
    lines = ["# BDI 抽取核对", "", "| # | 他说 | activity | desire | belief |", "|---|---|---|---|---|"]
    for e in extract:
        lines.append("| %d | %s | %s | %s | %s |" % (
            e["i"], e["text"][:20], e["activity"], e["desire"], e["belief"]))
    open(os.path.join(args.out, "extract_review.md"), "w", encoding="utf-8").write("\n".join(lines))

    rng = random.Random(20261028)
    blind, key = [], []
    for r in rows:
        swap = rng.random() < 0.5
        a, b = (r["bdi"], r["base"]) if swap else (r["base"], r["bdi"])
        blind.append(dict(i=r["i"], A=a, B=b))
        key.append(dict(i=r["i"], bdi_side="A" if swap else "B"))
    json.dump(blind, open(os.path.join(args.out, "blind.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    json.dump(key, open(os.path.join(args.out, "key.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("done", len(rows))
    nb.close()
    nd.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
