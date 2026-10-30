# -*- coding: utf-8 -*-
"""在本地 Qwen2.5-1.5B 上做 LoRA，学她的接话。

数据：evidence/p3/cmw_dataset/pairs.jsonl（完整上下文 → 她的回复）
系统提示：她的卡（cmw_import/persona.json）
只对回复段算 loss（prompt 段 -100）。

    python -m organism.train_lora --epochs 2
"""
import argparse
import json
import os

import torch
from torch.utils.data import Dataset
from transformers import (AutoModelForCausalLM, AutoTokenizer, Trainer,
                          TrainingArguments)


class Pairs(Dataset):
    def __init__(self, path, card, tok, max_len=256):
        self.rows = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if r.get("reply") and r.get("context"):
                    self.rows.append(r)
        self.card, self.tok, self.max_len = card, tok, max_len

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, i):
        r = self.rows[i]
        prompt = self.card + "\n\n【你收到的】\n" + r["context"][-2500:] + "\n\n你回："
        p = self.tok(prompt, add_special_tokens=False).input_ids
        a = self.tok(r["reply"], add_special_tokens=False).input_ids + [self.tok.eos_token_id]
        p = p[-(self.max_len - len(a)):] if len(p) + len(a) > self.max_len else p
        ids = p + a
        return dict(input_ids=torch.tensor(ids), labels=torch.tensor([-100] * len(p) + a))


def collate(batch):
    L = max(len(b["input_ids"]) for b in batch)
    ids = torch.full((len(batch), L), 0, dtype=torch.long)
    lab = torch.full((len(batch), L), -100, dtype=torch.long)
    mask = torch.zeros((len(batch), L), dtype=torch.long)
    for i, b in enumerate(batch):
        n = len(b["input_ids"])
        ids[i, :n] = b["input_ids"]
        lab[i, :n] = b["labels"]
        mask[i, :n] = 1
    return dict(input_ids=ids, labels=lab, attention_mask=mask)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="evidence/p3/cmw_dataset/pairs.jsonl")
    ap.add_argument("--model", default="models/qwen2.5-1.5b-instruct")
    ap.add_argument("--out", default="models/cmw-lora-1.5b")
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--lr", type=float, default=1e-4)
    args = ap.parse_args(argv)

    with open("evidence/p3/cmw_import/persona.json", encoding="utf-8") as f:
        card = json.load(f)["card"]
    tok = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        args.model, dtype=torch.bfloat16, low_cpu_mem_usage=True, trust_remote_code=True)
    model = model.to("cuda")
    model.gradient_checkpointing_enable()
    from peft import LoraConfig, get_peft_model
    model = get_peft_model(model, LoraConfig(
        r=8, lora_alpha=16, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"]))
    model.print_trainable_parameters()

    ds = Pairs(args.data, card, tok)
    print("pairs", len(ds))
    targs = TrainingArguments(
        output_dir=args.out, per_device_train_batch_size=1,
        gradient_accumulation_steps=8, num_train_epochs=args.epochs,
        learning_rate=args.lr, logging_steps=10, save_strategy="no",
        bf16=True, report_to=[], remove_unused_columns=False,
        dataloader_num_workers=0, gradient_checkpointing=True)
    tr = Trainer(model=model, args=targs, train_dataset=ds, data_collator=collate)
    tr.train()
    model.save_pretrained(args.out)
    tok.save_pretrained(args.out)
    print("saved", args.out)


if __name__ == "__main__":
    raise SystemExit(main())
