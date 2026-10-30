# 预注册：披露策略层（AADE 第 3 层）

2026-10-30。目标：决定"说不说、说多少"，而不是每句都报状态。

## 文献

- Rimé 社会分享：有情绪会跟亲近的人讲（EJSP 2013）
- Altman & Taylor 社会渗透：披露深度随关系
- Petronio CPM：场合/听众决定披露
- Scarantino 情感语用学：表达是社会行为
- [RECALLbot](https://dl.acm.org/doi/pdf/10.1145/3772318.3790714)：互惠披露
- [IVA 伴侣披露水平研究](https://dl.acm.org/doi/full/10.1145/3806774.3827968)

## 规则（先验，不做拟合）

输入：强度、关系（私聊他/群/其他）、他是否在问感受、今天是否已说过
输出：none / brief / elaborate / seek_response

1. 群里、或不熟：默认 none；被直接问且强度高 → brief
2. 私聊他：被问 → brief（高强度可 elaborate）；没问但强度很高且孤独 → seek_response
3. 今天已说过同一状态 → none 或 brief（不重复念）
4. 强度低 → none

## 判据

- 群聊过度披露率 ≤5%
- 私聊被问时"回避率" ≤10%
- 重复念状态率 ≤5%
- 人工抽检 20 条：不合适披露 ≤10%

## 回滚

`disclosure.enabled=false`；不影响现有表达。
