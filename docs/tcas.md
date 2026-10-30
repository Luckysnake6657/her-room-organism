# TCAS 四流与本项目证据映射

依据：Hughes & Nguyen (2026), AAAI-SS 8(1):262，
*Triangulating Evidence for Machine Consciousness Claims*。
四流：B 行为电池 / M 机制指标 / P 扰动测试 / O 观察者混淆控制。
关键规则：**缺流时不得给出 credence band**（missing-stream rule）。

## B 流：行为电池（带鲁棒性控制）

| 证据 | 文件 | 状态 |
|---|---|---|
| 6 条件 × 150 seeds 行为指标 | `evidence/ablation.jsonl` | 完整 |
| random 对照 | 同上，106/150 死亡 vs baseline 0/150 | 完整 |
| 动态任务（危险游走） | `evidence/ablation_v2_dynamic.jsonl` | 完整 |
| 身份 2×2 | `evidence/identity.jsonl` | 完整（探索性，未预注册） |

鲁棒性控制：配对设计（同 seed 同地图）、Bonferroni 校正、置换检验。

## M 流：机制指标（显式假设）

| 证据 | 文件 | 状态 |
|---|---|---|
| Butlin 14 项逐项 | `evidence/butlin_assessment.md` | 7/14 达 L3+ |
| 每项的代码位置 | `src/*.py` | 完整 |
| 热回路校准 | `src/thermo_body.py` + `evidence/thermal.jsonl` | 完整 |

显式假设：Butlin 的指标是"提高置信度"的证据，不是判决。

## P 流：扰动测试（因果敏感性 + 代理失效）

| 证据 | 文件 | 状态 |
|---|---|---|
| workspace 消融 | p<0.001，5 指标 | 完整 |
| self_model 消融 | 一阶不变、元认知崩溃 | 完整 |
| interoception 消融 | 进食 p=0.052 | 完整 |
| valence 消融 | 全阴性 | 完整（阴性） |
| prediction 消融 | v2 有害 | 完整（阴性） |

代理失效：**Φ 未计算**；IIT 代理（PCI-A）未接。

## O 流：观察者混淆控制

| 证据 | 状态 |
|---|---|
| random 对照 | 完整 |
| 模板化报告（语言器官 + guard） | 完整 |
| 盲评流程 | **缺失** |
| 评分者间一致性 | **缺失** |

缺口：P 流的"代理失效"与 O 流的"盲评"没有做实。

## 结论：可以给 credence 吗

按 missing-stream rule，**不能**。四流里：
- B、M、P 有数据但 P 缺"代理失效"（Φ/PCI 未测）
- O 缺盲评

因此本项目**不给分数、不给 credence band**，只给逐项证据与阴性清单。
这与 AIVA 类工作（声称 11.5/14）的差别就在这里。

## 要补齐缺什么

1. P 流：至少算一次 Φ（玩具系统，8–12 单元），或明确声明"不做，理由是没有可解释的粗粒化"。
2. O 流：设计一个盲评——把 baseline 与消融的日志去掉条件标签，交给人/另一个模型判断差异，看是否能分辨。
3. 补完后才谈 credence。
