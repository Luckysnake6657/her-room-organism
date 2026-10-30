# -*- coding: utf-8 -*-
"""LLM 基线 3 次重复：同卷同选项，报中位数与范围。"""
import json

from . import llm_quiz100


def main():
    runs = []
    for i in range(3):
        llm_quiz100.main()
        runs.append(json.load(open("evidence/p3/quiz100_llm.json", encoding="utf-8")))
    json.dump(runs, open("evidence/p3/quiz100_llm_runs.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    # 逐题一致性
    agree = sum(1 for n in map(str, range(1, 101))
                if len({r[n] for r in runs}) == 1)
    print("runs", len(runs), "identical_items", agree)


if __name__ == "__main__":
    main()
