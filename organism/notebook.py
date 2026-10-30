# -*- coding: utf-8 -*-
"""本子：你们的过去。用户产生、可改可删、带置信度。

规矩（roadmap §1.2 + memory-confidence-gate.md）：
- **写**：高置信低风险自动入；高风险（关系/承诺/健康）建 pending，问一句再确认。
- **读**：每轮 0–3 条；低于阈值的不作为事实注入。
- **断言**：回复里出现"你上次/你说过/我记得"，必须有够格的条目支撑，
  否则换成"这个我没记。"——门控的是**断言这个动作**，不是措辞。
- 置信度不靠 LLM 自评：v0 用来源规则（用户明说 0.9 / 确认过 0.95 / 推断 0.5），
  留 `calib` 字段给以后的 conformal 校准。

v0 不做自动抽取：写本子要么显式 `add`，要么 `propose` 出一条 pending 等用户确认。
"""
import json
import os
import time

THETA = 0.70                 # 低于这个置信度，不许当事实用
MAX_READ = 3                 # 每轮最多注入几条
ASSERT_MARKERS = ("你上次", "你说过", "你之前说", "你告诉过我",
                  "我们说过", "我们说好", "我记得", "记不记得",
                  "记住了", "你说得对", "那事儿")
QUERY_MARKERS = ("你记得", "还记得", "记得吗", "记得吧", "记不记得",
                 "我说过", "我跟你说过", "我上次", "我是不是说过")
WH_MARKERS = ("什么时候", "哪天", "是什么来着", "叫什么", "多长时间", "来着")
REFUSAL = "这个我没记。"


STOP_BIGRAMS = {"你还", "还记", "记得", "什么", "怎么", "时候", "现在", "我们", "你们",
                "他们", "这个", "那个", "就是", "可以", "没有", "知道", "觉得", "的事",
                "查的", "事吗", "一下", "不是", "真的"}


def _bigrams(s: str) -> set:
    s = "".join(ch for ch in s if ch.strip())
    if len(s) < 2:
        return {s} if s else set()
    return {s[i:i + 2] for i in range(len(s) - 1)} - STOP_BIGRAMS


def overlap(a: str, b: str) -> float:
    A, B = _bigrams(a), _bigrams(b)
    if not A or not B:
        return 0.0
    if len(a) == 1:          # 单字查询（"辣""猫"）也要能命中
        return 1.0 if a in b else 0.0
    # 按**查询**覆盖算，不按较短的一边：否则"记得…的事"这种填充词会把长条目拉成强相关
    return len(A & B) / len(A)


def has_support(sentence: str, provided, theta: float = THETA) -> bool:
    for e in provided:
        if e["confidence"] >= theta and overlap(
                sentence, e["text"] + " " + e.get("keywords", "")) >= 0.10:
            return True
    return False


def quote(entry: dict) -> str:
    """嘴没复述对时，从本子照念——比说"不记得"诚实，也比编造安全。"""
    return "你上次说：%s。" % entry["text"]


def gate_reply(text: str, provided, user_text: str = None,
               theta: float = THETA) -> tuple:
    """拦"断言"和"回答记忆问题"两种动作。

    1. 用户在问记忆（"你记得…/我说过…"）且本子没有够格条目 → 必须拒。
    2. 回复在断言记忆，但没有支撑 → 换掉。
    """
    asked = (user_text is not None
             and (any(m in user_text for m in QUERY_MARKERS)
                  or (provided and any(m in user_text for m in WH_MARKERS))))
    if asked:
        if not has_support(text, provided, theta):
            return REFUSAL, True
        return text, False
    if not any(m in text for m in ASSERT_MARKERS):
        return text, False
    if has_support(text, provided, theta):
        return text, False
    return REFUSAL, True


class Notebook:
    def __init__(self, path: str = None):
        self.path = path
        self.entries = []
        self._next = 1
        self.outcomes = []      # [(confidence, correct)] 用户确认/纠正的样本
        if path and os.path.exists(path):
            self.load()

    # ------------------------------------------------------------ 写
    def add(self, text: str, type: str = "fact", source: str = "",
            confidence: float = 0.90, status: str = "confirmed",
            importance: float = 0.5) -> dict:
        e = dict(id=self._next, type=type, text=text, source=source,
                 created_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
                 confidence=float(confidence), status=status, calib=None,
                 importance=float(importance), strength=1.0,
                 last_access=time.strftime("%Y-%m-%dT%H:%M:%S"),
                 keywords=text, atomic=None)
        try:
            from .atomic import is_atomic
            e["atomic"] = is_atomic(text)
        except Exception:
            pass
        self._next += 1
        self.entries.append(e)
        self.save()
        return e

    def propose(self, text: str, source: str = "", type: str = "event") -> dict:
        """高风险条目：先 pending，问一句再确认。"""
        return self.add(text, type=type, source=source, confidence=0.60,
                        status="pending", importance=0.9)

    def confirm(self, entry_id: int) -> dict:
        return self.update(entry_id, status="confirmed", confidence=0.95)

    def update(self, entry_id: int, **kw) -> dict:
        for e in self.entries:
            if e["id"] == entry_id:
                old = e["text"]
                e.update(kw)
                if "text" in kw and kw["text"] != old:
                    # 纠正后保留旧说法做检索键，否则"改名"之后就找不到了
                    e["keywords"] = e.get("keywords", old) + "，" + kw["text"]
                self.save()
                return e
        raise KeyError(entry_id)

    def delete(self, entry_id: int) -> None:
        self.update(entry_id, status="deleted")

    # ------------------------------------------------------------ 读
    def live(self):
        return [e for e in self.entries if e["status"] != "deleted"]

    def retrieve(self, query: str, k: int = MAX_READ, theta: float = THETA) -> list:
        scored = []
        for e in self.live():
            if e["confidence"] < theta or e["status"] == "pending":
                continue
            s = overlap(query, e["text"] + " " + e.get("keywords", ""))
            if s > 0:
                scored.append((s, e))
        scored.sort(key=lambda x: -x[0])
        return [e for _, e in scored[:k]]

    def has_support(self, sentence: str, provided, theta: float = THETA) -> bool:
        return has_support(sentence, provided, theta)

    # ------------------------------------------------------------ 断言门
    def gate(self, text: str, provided) -> tuple:
        return gate_reply(text, provided)

    # ------------------------------------------------------------ 存
    def save(self):
        if not self.path:
            return
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(dict(next=self._next, entries=self.entries,
                           outcomes=self.outcomes), f, ensure_ascii=False, indent=2)

    def load(self):
        with open(self.path, encoding="utf-8") as f:
            d = json.load(f)
        self.entries = d["entries"]
        self._next = d.get("next", len(self.entries) + 1)
        self.outcomes = d.get("outcomes", [])

    # ---------------------------------------------------------------- 校准
    MIN_OUTCOMES = 10

    def record_outcome(self, entry: dict, correct: bool):
        """用户确认/纠正一次：作为校准样本，并重算本子的校准置信。"""
        self.outcomes.append([float(entry["confidence"]), 1 if correct else 0])
        entry.setdefault("outcomes", []).append([float(entry["confidence"]), 1 if correct else 0])
        if not correct:
            entry["contested"] = True
        self.calibrate_all()
        self.save()

    def calibrate_all(self):
        """先按条目自己的 outcome 校准；不够 MIN 才退回全局先验。"""
        from . import calib
        table = None
        if len(self.outcomes) >= self.MIN_OUTCOMES:
            table = calib.bin_means([(c, y) for c, y in self.outcomes], bins=5)
        for e in self.entries:
            own = e.get("outcomes") or []
            if len(own) >= self.MIN_OUTCOMES:
                t = calib.bin_means([(c, y) for c, y in own], bins=5)
                e["calibrated"] = round(calib.calibrate(e["confidence"], t), 3)
            else:
                e["calibrated"] = e["confidence"]
