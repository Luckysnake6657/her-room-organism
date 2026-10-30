# -*- coding: utf-8 -*-
"""LLM 抽取用户事实（影子本子）。文献：OpenIE / Mem0 / Generative Agents 反思。"""
import json
import os
import re

from . import api_client, notebook

P = """从下面这些"他"发的消息里，抽出关于他的**事实**（计划、偏好、健康、关系、工作、经历）。
要求：
- 每条一句，第三人称"他…"
- 只写事实，不写提问、不写情绪评价、不写工程/配置/日志
- 没有事实就输出 []
- 只输出 JSON 数组

消息：
"""


def main():
    home = "evidence/p3/shadow_userfacts"
    os.makedirs(home, exist_ok=True)
    path = os.path.join(home, "notebook.json")
    if not os.path.exists(path):
        json.dump({"next": 1, "entries": []}, open(path, "w", encoding="utf-8"))
    nb = notebook.Notebook(path)
    seen = {e["text"] for e in nb.entries}
    msgs = []
    for line in open("evidence/p3/cmw_messages/messages.jsonl", encoding="utf-8"):
        d = json.loads(line)
        if d.get("isSelf") or not d.get("isOwner"):
            continue
        t = re.sub(r"\[[^\]]*\]", "", d.get("text") or "").strip()
        if len(t) >= 4:
            msgs.append(t)
    added = 0
    for start in range(0, len(msgs), 10):
        chunk = msgs[start:start + 10]
        body = "\n".join("- " + m[:80] for m in chunk)
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
            nb.add(f, type="fact", source="user_shadow_llm", confidence=0.75)
            seen.add(f)
            added += 1
    print("added", added, "total", len(nb.entries))


if __name__ == "__main__":
    main()
