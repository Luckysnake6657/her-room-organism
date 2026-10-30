# 生活/办事双模式：理论机制对照

2026-10-28。目标：她有自己的日子，也能陪你解决问题，但不变成客服。

## 理论 → 机制 → 代码

| 理论 | 机制 | 代码 |
|---|---|---|
| Blumberg 1996：内在需要驱动行为 | 六状态 + D（可行域偏离） | `model.py`、`form.py` |
| Generative Agents 2023：自己的日程与反思 | 日记、成长回路、主动开口 | `native.py`、`diary` |
| **Horvitz 1999：混合主动，收益 > 打扰成本才介入** | **life/task/defer 判定** | `intent.decide_mode` |
| Bickmore 2005：长期关系靠连续 | 单流记忆、regard/U | `notebook.py`、`native.ingest` |
| Deci & Ryan：自主/胜任/归属 | 拒绝权、不 24h 待命 | `defer` 分支、`no_question` |
| Mateas & Stern 2003：角色有自己的目标 | 可以先不帮、可以不同意 | `defer`、`guarded` |

## 决策规则

```
wants_task = 明确请求词（帮我/查一下/报错/代码/文件…）
if not wants_task: life
elif a > 0.70 or e < 0.25 or D > 1.6: defer   # 介入成本过高
else: task
```

- task：可以说细、分点、该用工具就用
- life：短、口语、别像办事
- defer：固定一句"现在有点累，晚点行吗"（不走模型，省成本，也不装）

## 哪些是理论支持的

- **默认过日子、按需介入**：Horvitz 的介入成本
- **有自己的状态/日程**：Blumberg / Generative Agents
- **可以拒绝**：自我决定论（自主）
- **连续性**：Bickmore

## 哪些是设计假设（还没证据）

- 具体阈值（0.70 / 0.25 / 1.6）
- "明确请求词"能覆盖中文的真实请求方式
- defer 的频率不会让人烦

## 判据（先写死）

1. 50 条真实消息，mode 与人工标注一致 ≥85%
2. task 轮次占比 <50%
3. defer 后用户接受，不重复触发
4. 一周内至少一次"她主动提起上次的事"

## 已知缺口

- DSH 的工具白名单还没按 mode 开关（现在只注入"办事"提示）
- native 自己的工具层没有
- 主动开口还没接 QQ

## 下一步

拿 50 条真实消息标注，验第 1 条；不过 85% 就调阈值，不调框架。
