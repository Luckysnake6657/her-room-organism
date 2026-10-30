# -*- coding: utf-8 -*-
"""30 条标签 vs 分类器预测。"""
import json

LABELS = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0, 7: 0, 8: 0, 9: 1, 10: 0,
          11: 1, 12: 0, 13: 0, 14: 0, 15: 0, 16: None, 17: 0, 18: 0, 19: 0,
          20: 0, 21: 0, 22: 1, 23: 0, 24: 0, 25: 0, 26: 1, 27: 0, 28: 0,
          29: 0, 30: 0}


def main():
    preds = json.load(open("evidence/p3/joke30_predictions.json", encoding="utf-8"))
    tp = fp = fn = tn = 0
    missed, false_pos = [], []
    for i in range(1, 31):
        y = LABELS.get(i)
        if y is None:
            continue
        p = bool(preds[i - 1])
        if y and p:
            tp += 1
        elif y and not p:
            fn += 1
            missed.append(i)
        elif not y and p:
            fp += 1
            false_pos.append(i)
        else:
            tn += 1
    n = tp + fp + fn + tn
    out = dict(n=n, tp=tp, fp=fp, fn=fn, tn=tn,
               precision=round(tp / (tp + fp), 3) if tp + fp else 0,
               recall=round(tp / (tp + fn), 3) if tp + fn else 0,
               f1=round(2 * tp / (2 * tp + fp + fn), 3) if tp + fp + fn else 0,
               accuracy=round((tp + tn) / n, 3),
               base_rate=round((tp + fn) / n, 3),
               missed=missed, false_pos=false_pos,
               predicted_yes=[i + 1 for i, p in enumerate(preds) if p])
    json.dump(out, open("evidence/p3/joke30_score.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps({k: out[k] for k in ("n", "tp", "fp", "fn", "tn", "precision",
                                          "recall", "f1", "accuracy", "base_rate")},
                     ensure_ascii=False))
    print("missed", missed, "false_pos", false_pos, "pred_yes", out["predicted_yes"])


if __name__ == "__main__":
    main()
