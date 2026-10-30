# -*- coding: utf-8 -*-
"""从她的话里抽"关于他"的事实（影子）。"""
import json
import os
import random
import re

from . import api_client, notebook

P = """下面是她说过的话。从中抽出**关于"他"的事实**（他的计划、偏好、健康、关系、工作、经历）。
要求：每条一句，第三人称"他…"；只写事实，不写情绪/评价/工程日志；没有就输出 []。
只输出 JSON 数组。

她的话：
"""


def main():
    path = "evidence/p3/shadow_userfacts/notebook.json"
    nb = notebook.Notebook(path)
    seen = {e["text"] for e in nb.entries}
    lines = []
    for line in open("evidence/p3/cmw_sessions/her_lines.jsonl", encoding="utf-8"):
        d = json.loads(line)
        t = (d.get("text") or "").strip()
        if len(t) >= 6 and ("他" in t or "你" in t):
            lines.append(t)
    rng = random.Random(7)
    rng.shuffle(lines)
    lines = lines[:600]
    added = 0
    for start in range(0, len(lines), 10):
        chunk = lines[start:start + 10]
        body = "\n".join("- " + c[:80] for c in chunk)
        arr = None
        for _ in range(2):
            try:
                raw = api_client.chat(P + body, "", max_tokens=1200, temperature=0.2)
            except Exception:
                continue
            m = re.search(r"\[.*\]", raw, re.S)
            if m:
                try:
                    arr = json.loads(m.group(0))
                    break
                except Exception:
                    pass
        for f in (arr or []):
            f = str(f).strip()
            if len(f) < 6 or f in seen:
                continue
            nb.add(f, type="fact", source="her_lines_shadow", confidence=0.75)
            seen.add(f)
            added += 1
    print("added", added, "total", len(nb.entries))


if __name__ == "__main__":
    main()
