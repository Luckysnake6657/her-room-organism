# -*- coding: utf-8 -*-
"""文体计量旁证：用"她 vs 他"的字符 n-gram 分类器，给 A/B 打分。

不是替代盲读，是旁证：P(她) 越高越像她的文风。
"""
import json

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_predict
from sklearn.metrics import roc_auc_score

HER = "evidence/p3/cmw_sessions/her_lines.jsonl"
MSG = "evidence/p3/cmw_messages/messages.jsonl"
BLIND = "evidence/p3/persona_blind3.json"


def load():
    her = []
    for line in open(HER, encoding="utf-8"):
        t = (json.loads(line).get("text") or "").strip()
        if len(t) >= 4:
            her.append(t)
    him = []
    for line in open(MSG, encoding="utf-8"):
        d = json.loads(line)
        t = (d.get("text") or "").strip()
        if d.get("isOwner") and not d.get("isSelf") and len(t) >= 4:
            him.append(t)
    return her, him


def main():
    her, him = load()
    n = min(len(her), len(him))
    X = her[:n] + him[:n]
    y = np.array([1] * n + [0] * n)
    vec = TfidfVectorizer(analyzer="char", ngram_range=(1, 3), min_df=2, max_features=30000)
    M = vec.fit_transform(X)
    clf = LogisticRegression(max_iter=1000)
    prob = cross_val_predict(clf, M, y, cv=5, method="predict_proba")[:, 1]
    auc = roc_auc_score(y, prob)
    clf.fit(M, y)
    rows = json.load(open(BLIND, encoding="utf-8"))
    out = []
    for r in rows:
        rec = dict(context=r["context"])
        for lab, text in (r["first"], r["second"]):
            rec[lab] = round(float(clf.predict_proba(vec.transform([text]))[0, 1]), 3)
        out.append(rec)
    a = [r["A"] for r in out]
    b = [r["B"] for r in out]
    res = dict(cv_auc=round(float(auc), 3), n=len(out),
               A_mean=round(float(np.mean(a)), 3),
               B_mean=round(float(np.mean(b)), 3),
               B_wins=sum(1 for r in out if r["B"] > r["A"]),
               rows=out)
    json.dump(res, open("evidence/p3/persona_authorship.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(json.dumps({k: res[k] for k in ("cv_auc", "n", "A_mean", "B_mean", "B_wins")},
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
