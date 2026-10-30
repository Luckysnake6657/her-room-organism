# -*- coding: utf-8 -*-
"""预注册 manifest：每个 prereg 文件的 sha256 + 当前 commit，供第三方核查。"""
import hashlib
import os
import subprocess

out = ["# 预注册 manifest", "",
       "生成时间：2026-10-29。每个文件在**结果之前**写入；sha256 可校验未被改动。", ""]
try:
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
except Exception:
    commit = "unknown"
out += ["当前 commit：`%s`" % commit, "",
        "| 文件 | sha256 |", "|---|---|"]
files = sorted(f for f in os.listdir("docs")
               if "prereg" in f.lower() or "pre-reg" in f.lower())
for f in files:
    h = hashlib.sha256(open(os.path.join("docs", f), "rb").read()).hexdigest()
    out.append("| %s | `%s` |" % (f, h[:32]))
open("docs/prereg-manifest.md", "w", encoding="utf-8").write("\n".join(out) + "\n")
print("hashed", len(files), "prereg files; commit", commit[:7])
