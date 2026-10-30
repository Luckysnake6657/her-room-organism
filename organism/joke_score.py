# -*- coding: utf-8 -*-
"""反讽分类器 vs 人工 100 条标签：混淆矩阵/精确率/召回率。"""
import json
import re

RAW = """梗，常，梗，常，常，常，常，梗，常，常，常，常，常，常，常，常，常，常，常，常，
常，常，梗，梗，梗，常，常，常，常，常，常，常，常，常，常，常，常，常，常，常，常，常，常，
常，常，常，常，常，常，常，常，51.梗，常，梗（也算是偏调侃了），常，常，常，常，常，常，
60.梗（略微偏向于调侃，语气比较无奈的那种），常，常，常，常，常，常，常，梗，梗，70.常，
常，梗，常，常，常，常，常，常，常，80.常，常，常，常，常，常，常，常，常，常，90.常，梗，
常，常，常，常，常，常，常，常，常"""


def parse_label(tok):
    if "梗" in tok:
        return 1
    if "常" in tok:
        return 0
    return None


def main():
    tokens = [t.strip() for t in re.split(r"[，,]", RAW) if t.strip()]
    labels = {}
    nxt = 1
    for tok in tokens:
        m = re.match(r"^(\d+)\s*[\.、]?\s*(.*)$", tok)
        if m and int(m.group(1)) <= 100 and parse_label(m.group(2)) is not None:
            idx = int(m.group(1))
            labels[idx] = parse_label(m.group(2))
            nxt = idx + 1
        else:
            lab = parse_label(tok)
            if lab is None:
                continue
            labels[nxt] = lab
            nxt += 1
    preds = json.load(open("evidence/p3/joke_predictions.json", encoding="utf-8"))
    pairs = [(i, labels[i], bool(preds[i - 1])) for i in range(1, 101) if i in labels]
    tp = sum(1 for _, y, p in pairs if y == 1 and p)
    fp = sum(1 for _, y, p in pairs if y == 0 and p)
    fn = sum(1 for _, y, p in pairs if y == 1 and not p)
    tn = sum(1 for _, y, p in pairs if y == 0 and not p)
    out = dict(n=len(pairs), labeled=len(labels), tp=tp, fp=fp, fn=fn, tn=tn,
               precision=round(tp / (tp + fp), 3) if tp + fp else 0,
               recall=round(tp / (tp + fn), 3) if tp + fn else 0,
               f1=round(2 * tp / (2 * tp + fp + fn), 3) if tp + fp + fn else 0,
               accuracy=round((tp + tn) / len(pairs), 3))
    json.dump(out, open("evidence/p3/joke_score.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps(out, ensure_ascii=False))
    print("missed", [i for i, y, p in pairs if y == 1 and not p])
    print("false_pos", [i for i, y, p in pairs if y == 0 and p])


if __name__ == "__main__":
    main()
