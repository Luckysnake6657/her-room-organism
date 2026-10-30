# -*- coding: utf-8 -*-
"""用户模型验证：按天留出，预测他某小时是否活跃（AUC）。"""
import json
import random
import time

from sklearn.metrics import roc_auc_score

from . import usermodel as U


def load():
    recs = []
    for line in open("evidence/p3/cmw_messages/messages.jsonl", encoding="utf-8"):
        d = json.loads(line)
        t = float(d.get("t") or 0)
        if t > 1e12:
            t /= 1000.0
        recs.append((t, d.get("text") or "", bool(d.get("isOwner")) and not d.get("isSelf")))
    return [r for r in recs if r[0] > 0]


def daykey(ts):
    return time.strftime("%Y-%m-%d", time.localtime(ts))


def main():
    recs = load()
    days = sorted({daykey(t) for t, _, _ in recs})
    cut = int(len(days) * 0.8)
    train_days, test_days = set(days[:cut]), set(days[cut:])
    train = [r for r in recs if daykey(r[0]) in train_days]
    m = U.fit(train)
    if not m:
        print("no model")
        return
    y, s = [], []
    for t, _, owner in recs:
        if daykey(t) not in test_days or not owner:
            continue
        y.append(1)
        s.append(m["hour_prob"][time.localtime(t).tm_hour])
    # 负样本：测试天里没有消息的小时
    for d in sorted(test_days):
        for h in range(24):
            if not any(daykey(t) == d and time.localtime(t).tm_hour == h and o for t, _, o in recs):
                y.append(0)
                s.append(m["hour_prob"][h])
    auc = roc_auc_score(y, s)
    rng = random.Random(0)
    ys = y[:]
    rng.shuffle(ys)
    ctrl = roc_auc_score(ys, s)
    out = dict(n=len(y), train_days=len(train_days), test_days=len(test_days),
               auc=round(float(auc), 3), control=round(float(ctrl), 3),
               len_p50=m["len_p50"], neg_rate=m["neg_rate"])
    json.dump(out, open("evidence/p3/usermodel_eval.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    U.save(m)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
