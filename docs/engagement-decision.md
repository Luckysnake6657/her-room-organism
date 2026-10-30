# 介入决策：从分类改成定价

2026-10-28。起因：`life/task` 关键词分类在留出集上只有 **43%**，方法不成立。

## 文献

- Horvitz, *Principles of Mixed-Initiative User Interfaces*, CHI 1999。
- An, *When Should the Agent Speak? A Survey of Intervention Timing for Always-On AI Assistants*, TMLR 2026。
  <https://tmlr.infinite-conf.org/paper_pages/b0yKEdAXEr.html>
  核心：**intervene iff expected benefit > expected cost of interrupting**；
  并指出"评价是门槛层"——没有 outcome，就无法训练/验证主动性。

## 方法

不做二分类，算一次"介入定价"：

```
benefit = 0.5·明确度 + 0.3·事情价值 + 0.2·关系
cost    = 0.35·应激 + 0.25·(1−精力) + 0.20·D/2 + 0.10·U
net     = benefit − cost − 不确定惩罚
```

- `now`：完整回应（可长、可用工具）
- `brief`：短回（≤20 字）
- `later`：固定一句"现在有点累，晚点行吗"

明确度：强请求词 1.0；疑问/弱请求 0.5；陈述 0.0。
不确定惩罚：弱请求 +0.10（风险敏感，宁可短）。

## 校准

阈值（0.30 / −0.10）是按分布选的，不是按 outcome 学的：

- 正常状态：陈述 → brief；问句/请求 → now
- 状态差：闲聊 → later；强请求 → brief

## 评价缺口（必须说）

综述说评价是门槛；我们没有"这次介入是否合适"的 outcome 标签。
现在只能做分布检查（不退化成全 now / 全 later），**不能声称决策正确**。

## 下一步

- 拿 20 段真实对话，人工判"她这次该 now/brief/later"，算一致率
- 或记录一周内 defer 后用户的反应（接受/重问/生气）

## 结论

**理论成立的是"按成本定价"，不是"把对话分两类"。**
关键词分类是错误实现，已替换。
