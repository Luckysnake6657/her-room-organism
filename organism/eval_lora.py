# -*- coding: utf-8 -*-
"""用微调后的本地模型，对同一批 20 对生成回复，供盲评。

    python -m organism.eval_lora --adapter models/cmw-lora-1.5b --out evidence/p3/shadow_lora
"""
import argparse
import json
import os
import random

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from . import corpus, notebook, retrieval, working


def build_prompt(card, recent, snippets, words_base, owner):
    lines = [card.strip(), "", "【现在】你刚看到他的消息，状态一般，不累不病。"]
    samples = corpus.pick(owner or "在吗", 8)
    if samples:
        lines.append("【你以前发消息的样子（只学语气和长度，别照抄）】")
        lines.extend("- " + s for s in samples)
    if recent:
        lines.append("【刚才你们在说】")
        lines.extend(working.prompt_lines(recent))
    if snippets:
        lines.append("【你记得的事】")
        lines.extend("- " + s for s in snippets)
    lines.append("")
    lines.append("回他一句，像平时发消息那样，%d 到 %d 个字。" % (max(6, words_base), words_base * 2))
    lines.append("不要解释，不要说自己是 AI，不要用书面语。只输出这一句。")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default="models/cmw-lora-1.5b")
    ap.add_argument("--state", default=r"D:\qq-bridge\state\social-v2.json")
    ap.add_argument("--import-dir", default="evidence/p3/cmw_import")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--words-base", type=int, default=8)
    ap.add_argument("--out", default="evidence/p3/shadow_lora")
    args = ap.parse_args(argv)

    from .shadow import load_msgs, pairs
    with open(os.path.join(args.import_dir, "persona.json"), encoding="utf-8") as f:
        card = json.load(f)["card"]
    nb = notebook.Notebook(os.path.join(args.import_dir, "notebook.json"))
    ps = pairs(load_msgs(args.state, "private:owner"))[-args.n:]

    tok = AutoTokenizer.from_pretrained("models/qwen2.5-1.5b-instruct")
    base = AutoModelForCausalLM.from_pretrained(
        "models/qwen2.5-1.5b-instruct", torch_dtype=torch.bfloat16, device_map="auto")
    from peft import PeftModel
    model = PeftModel.from_pretrained(base, args.adapter)
    model.eval()

    recent, rows = [], []
    for k, p in enumerate(ps):
        snips = [e["text"] for _, e in retrieval.retrieve(nb, p["owner"], k=3)]
        prompt = build_prompt(card, recent, snips, args.words_base, p["owner"])
        ids = tok(prompt, return_tensors="pt", truncation=True, max_length=1536).to(model.device)
        with torch.no_grad():
            out = model.generate(**ids, max_new_tokens=80, do_sample=True,
                                 temperature=0.9, top_p=0.9, pad_token_id=tok.eos_token_id)
        text = tok.decode(out[0][ids["input_ids"].shape[1]:], skip_special_tokens=True).strip()
        text = text.split("\n")[0][:120]
        rows.append(dict(i=k, owner=p["owner"], hers=p["hers"], ours=text))
        working.add(recent, "user", p["owner"])
        working.add(recent, "her", p["hers"])

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "pairs.jsonl"), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    rng = random.Random(20261028)
    blind, key = [], []
    for r in rows:
        swap = rng.random() < 0.5
        a, b = (r["ours"], r["hers"]) if swap else (r["hers"], r["ours"])
        blind.append(dict(i=r["i"], A=a, B=b))
        key.append(dict(i=r["i"], ours_side="A" if swap else "B"))
    with open(os.path.join(args.out, "blind.json"), "w", encoding="utf-8") as f:
        json.dump(blind, f, ensure_ascii=False, indent=2)
    with open(os.path.join(args.out, "key.json"), "w", encoding="utf-8") as f:
        json.dump(key, f, ensure_ascii=False, indent=2)
    lens = sorted(len(r["ours"]) for r in rows)
    print("done", len(rows), "median ours", lens[len(lens) // 2])


if __name__ == "__main__":
    raise SystemExit(main())
