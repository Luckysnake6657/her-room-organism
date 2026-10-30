# -*- coding: utf-8 -*-
"""从"关于你的事实"出 100 题；问句用用户口吻。"""
import json
import random
import re

from . import api_client, atomic

ONE = """下面是一条关于"他"的事实。请用"他"的口吻写一句问"她"的话，像他本人在问：
- 例如"你还记得我上次说要去哪儿吗"
- 问句不能包含答案本身
- 只输出这一句问题

事实："""

ABSENT = """写 20 条中文口语提问，问一个人生活里可能有、但下面事实里没有的细节。
用"你还记得我…吗"的口吻。只输出 JSON 数组。事实（节选）："""

BAD = re.compile(r"签到|禁言|截图|表情|群主|DSH|token|接口|配置|日志|代码|模拟器|微信|账号|测试|BUG|bug")


def pool():
    nb = json.load(open("evidence/p3/cmw_import/notebook.json", encoding="utf-8"))["entries"]
    out = []
    for e in nb:
        for s in re.split(r"[。！？\n]", e["text"]):
            s = s.strip(" ，、；：")
            if not (10 <= len(s) <= 60) or BAD.search(s):
                continue
            if not ("他" in s or "你" in s):
                continue
            if atomic.is_atomic(s) and s not in out:
                out.append(s)
    return out


def ask(fact):
    for _ in range(3):
        try:
            raw = api_client.chat(ONE + fact, "", max_tokens=300, temperature=0.2)
        except Exception:
            continue
        q = (raw.strip().splitlines() or [""])[0].strip(' "“”')
        if q and fact[:5] not in q and len(q) >= 6:
            return q
    return ""


def main():
    facts = pool()
    rng = random.Random(20261030)
    rng.shuffle(facts)
    items = []
    for f in facts:
        if len(items) >= 80:
            break
        q = ask(f)
        if not q:
            continue
        items.append(dict(kind="answerable", q=q, gold=f,
                          options=[f] + rng.sample([x for x in facts if x != f], 4)))
    body = "\n".join("- " + t[:60] for t in facts[:30])
    raw = api_client.chat(ABSENT, body, max_tokens=2500, temperature=0.5)
    m = re.search(r"\[.*\]", raw, re.S)
    absent = json.loads(m.group(0))[:20] if m else []
    for q in absent:
        items.append(dict(kind="absent", q=q, gold=None, options=rng.sample(facts, 4)))
    rng.shuffle(items)
    json.dump(items, open("evidence/p3/quiz100_data.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("items", len(items), "answerable", sum(1 for i in items if i["kind"] == "answerable"))


if __name__ == "__main__":
    main()
