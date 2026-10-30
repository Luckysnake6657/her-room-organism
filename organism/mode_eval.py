# -*- coding: utf-8 -*-
"""mode 判定校验：规则 vs 独立 LLM 标注，50 条真实用户消息。"""
import json
import re

from organism import api_client
from organism.intent import decide_mode
from organism.model import Body

RUBRIC = """给下面每条消息标一个模式，只输出 JSON（键是编号，值是 life/task）：
- task：他在请你办事（帮我看/查/写/改/弄/算/翻译/看报错/一起弄）
- life：其余（闲聊、问候、说自己的事、情绪、晚安）
不要解释，只输出 JSON。"""


def load_texts(n=50):
    rows = []
    for line in open("evidence/p3/cmw_messages/messages.jsonl", encoding="utf-8"):
        d = json.loads(line)
        if not d.get("isSelf") and d.get("isOwner"):
            t = re.sub(r"\[[^\]]*\]", "", d.get("text") or "").strip()
            if len(t) >= 4:
                rows.append(t)
    seen, out = set(), []
    for t in rows:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:n]


def llm_labels(texts):
    labels = {}
    for start in range(0, len(texts), 10):
        chunk = texts[start:start + 10]
        body = "\n".join("%d. %s" % (i + 1, t) for i, t in enumerate(chunk))
        raw = api_client.chat(RUBRIC, body, max_tokens=800, temperature=0.1)
        m = re.search(r"\{.*\}", raw, re.S)
        if not m:
            continue
        try:
            d = json.loads(m.group(0))
        except Exception:
            continue
        for k, v in d.items():
            try:
                labels[start + int(k)] = str(v).strip().lower()
            except Exception:
                pass
    return labels


def main():
    texts = load_texts(50)
    b = Body()
    rule = [decide_mode(b, t) for t in texts]
    lab = llm_labels(texts)
    pairs = [(i + 1, texts[i], rule[i], lab.get(i + 1, "?")) for i in range(len(texts))]
    agree = sum(1 for p in pairs if p[2] == p[3] and p[3] in ("life", "task"))
    print("n", len(texts), "labeled", sum(1 for p in pairs if p[3] in ("life", "task")))
    print("agreement", agree, "/", len(texts), "=", round(agree / len(texts), 2))
    for p in pairs:
        if p[2] != p[3]:
            print("DIFF", p[0], "rule", p[2], "llm", p[3])
    json.dump(dict(pairs=pairs, agree=agree, n=len(texts)),
              open("evidence/p3/mode_eval.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
