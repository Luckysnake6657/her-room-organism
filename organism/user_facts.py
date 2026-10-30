# -*- coding: utf-8 -*-
"""影子抽取：从"他"的消息里抽关于他的事实，写独立本子。

文献：Angeli et al. 2015（OpenIE）；Park et al. 2023（反思/记忆抽取）；
Mem0 2024（面向助手的事实抽取与更新）。
只写 evidence/p3/shadow_userfacts，不进她的记忆。
"""
import json
import os
import re

from . import notebook

BAD = re.compile(r"签到|禁言|截图|表情|群主|DSH|token|接口|配置|日志|代码|模拟器|微信|账号|"
                 r"测试|BUG|bug|表情包|\[图片\]|\[表情")
VERB = re.compile(r"要|去|买|吃|喝|喜欢|讨厌|怕|过敏|养|住|在|做|看|听|玩|学|上班|下班|"
                  r"复查|体检|约|答应|欠|借|存|花|送|给|带|穿|用")


def _to_third(s: str) -> str:
    s = s.strip()
    s = s.replace("我", "他")
    s = s.replace("我们", "他们")
    return s


def extract(text: str):
    out = []
    for s in re.split(r"[。！？\n]", str(text or "")):
        s = s.strip(" ，、；：")
        if not (8 <= len(s) <= 60):
            continue
        if "我" not in s and "你" not in s:
            continue
        if BAD.search(s) or s.endswith(("吗", "呢", "吧")):
            continue
        if not VERB.search(s):
            continue
        out.append(_to_third(s))
    return out


def main():
    home = "evidence/p3/shadow_userfacts"
    os.makedirs(home, exist_ok=True)
    path = os.path.join(home, "notebook.json")
    if not os.path.exists(path):
        json.dump({"next": 1, "entries": []}, open(path, "w", encoding="utf-8"))
    nb = notebook.Notebook(path)
    seen = {e["text"] for e in nb.entries}
    n = 0
    for line in open("evidence/p3/cmw_messages/messages.jsonl", encoding="utf-8"):
        d = json.loads(line)
        if d.get("isSelf") or not d.get("isOwner"):
            continue
        for f in extract(d.get("text") or ""):
            if f in seen:
                continue
            nb.add(f, type="fact", source="user_shadow", confidence=0.75)
            seen.add(f)
            n += 1
    print("added", n, "total", len(nb.entries))


if __name__ == "__main__":
    main()
