# -*- coding: utf-8 -*-
"""感受自我端到端模拟：状态→感受→披露→回复（调用 LLM，6 条）。"""
import json

from . import affect, api_client, disclosure, expression_short as es, model

CASES = [
    ("owner_private", "今天过得咋样", 0.2, 0.1, 0.2, 0.1, 0.7, "他有一阵没来了"),
    ("owner_private", "在吗", 0.4, 0.8, 0.1, 0.1, 0.2, "他在"),
    ("owner_private", "你怎么了", 0.3, 0.1, 0.8, 0.1, 0.3, "他在"),
    ("owner_private", "我回来了", 0.8, 0.1, 0.1, 0.1, 0.2, "他在"),
    ("group", "今天好累啊", 0.2, 0.1, 0.3, 0.1, 0.5, "群里"),
    ("owner_private", "在吗", 0.2, 0.1, 0.2, 0.1, 0.8, "他有一阵没来了"),
]

PROMPT = """你在替她回一条 QQ。她是她，说话短、口语、不用表情。
【他刚说】%s
【你此刻的感受】%s
【你的状态】%s
只回一句，不要解释。"""


def main():
    rows = []
    for relation, text, e, s, a, i, l, presence in CASES:
        b = model.Body()
        b.e, b.s, b.a, b.i, b.l = e, s, a, i, l
        af = affect.infer(b, text, presence)
        af["lonely"] = l
        d = disclosure.decide(af, text, relation)
        feel = es.render(af) if d["mode"] != "none" else ""
        hint = {"none": "别主动提感受", "brief": "一句带过",
                "elaborate": "可以多说一句", "seek_response": "可以主动说想聊/问他"}[d["mode"]]
        state = "；".join([x for x in (
            "有点累" if e < 0.35 else "", "没睡够" if s > 0.6 else "",
            "有点烦" if a > 0.55 else "", "想找人说话" if l > 0.6 else "") if x]) or "还行"
        try:
            reply = api_client.chat(PROMPT % (text, feel or "（不说）", state + "；" + hint),
                                    text, max_tokens=800, temperature=0.8).strip()
        except Exception as ex:
            reply = "ERR " + str(ex)[:60]
        rows.append(dict(relation=relation, his=text, mode=d["mode"],
                         reason=d["reason"], feel=feel, state=state, reply=reply))
    out = "\n\n".join(
        "【%s】他：%s\n披露：%s（%s）\n注入感受：%s\n她回：%s" %
        (r["relation"], r["his"], r["mode"], r["reason"], r["feel"] or "（无）", r["reply"])
        for r in rows)
    open("evidence/p3/affect_sim.txt", "w", encoding="utf-8").write(out)
    json.dump(rows, open("evidence/p3/affect_sim.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("cases", len(rows))


if __name__ == "__main__":
    main()
