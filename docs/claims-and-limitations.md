# Claims & Limitations（可直接贴进 manuscript）

写于 2026-10-26 晚。数字以 `docs/final-account-2026-10-26.md` 为准（Butlin 8/14）。

---

## 中文

### Claims（我们敢主张的）

1. **架构层**：一个 16×16 网格世界的觅食 agent，具备四个功能专门化的模块
   （内感受、视觉、危险、自我模型）与一个容量为 1 的竞争性工作空间；
   14 项 Butlin 指标中 **8 项达到 L3+**（6 项 L4、2 项 L3）。
2. **工作空间有因果力**：对工作空间做 do() 干预可改变选择概率与行为
   （3.4%→13.1%；4.8%→12.1%，p<0.0001，带安慰剂对照）；
   **广播内容**（而非仅广播这一动作）有特异作用：内容对照无效（p=1.00），
   象限门控有效（0.844 vs 0.409，p<0.0001）。
3. **关键通道必要性**：视觉通道去掉后进食 3.98→2.87、危险 2.57→9.15、死亡 5%→67%。
4. **方法学**：三次自我更正（EI 填充伪影、效价恒零、sham 对照推翻视觉特异性），
   全部预注册、可复现、append-only 台账（`broken=0`）。
5. **理论反例**：在 60 个 4 节点布尔网络上，Φ 与分支比 λ 正相关（ρ=0.648，p<0.0001），
   峰在混沌区（λ≈1.8）而非临界点（λ≈1）；且同一 λ 下 Φ 可差 10 倍
   ——**Φ 不是 λ 的函数**。

### Limitations（必须写的）

1. **IIT 不成立**：本 agent 的 Φ 为 0.004–0.011，与打乱零模型不可区分；
   分支比 σ=0.42 属亚临界。**目标系统不在高 Φ 区**。
2. **对照覆盖不足**：8 项 met 中只有 GWT-3 有排除替代解释的对照；
   RPT-1 缺等参数量递归基线、HOT-2 缺置信度分布匹配、
   AST-1 缺无关通道对照、AE-2 缺 yoked sham-feedback。
3. **特异性弱**：视觉消融的 sham 对照（随机内容）与完全去掉同样严重
   （3.05 vs 2.80；危险 10.20 vs 8.97），故只能主张"通道必要性"，不能主张"功能特异性"。
4. **多重比较**：全项目 55 个 p 值，BH(FDR=0.05) 后 24 个仍显著；检验间高度相关，FDR 仅为近似。
5. **外部效度**：16×16 网格世界与任何真实系统相去甚远；
   Φ–λ 反例仅限 n=4 确定性布尔网络。

---

## English

### Claims

1. **Architecture.** A 16×16 foraging agent with four functionally specialised modules
   (interoception, vision, danger, self-model) and a capacity-1 competitive workspace;
   **8 of 14 Butlin indicators reach L3+** (6 L4, 2 L3).
2. **The workspace has causal power.** do()-interventions on the workspace change
   selection probabilities and behaviour (3.4%→13.1%; 4.8%→12.1%, p<0.0001, with
   placebo controls). The *content* of the broadcast matters: a content control is null
   (p=1.00) whereas quadrant gating is effective (0.844 vs 0.409, p<0.0001).
3. **A key channel is necessary.** Removing the visual channel moves foraging from
   3.98 to 2.87, hazard hits from 2.57 to 9.15, and mortality from 5% to 67%.
4. **Methodology.** Three self-corrections (an EI fill artefact, a degenerate valence
   pathway, and a sham-controlled refutation of visual specificity), all pre-registered,
   reproducible, with an append-only ledger (`broken=0`).
5. **A theoretical counter-example.** Across 60 four-node Boolean networks, Φ correlates
   with the branching ratio λ (ρ=0.648, p<0.0001), peaking in the chaotic regime
   (λ≈1.8) rather than at criticality (λ≈1); and at matched λ the Φ values differ by an
   order of magnitude. **Φ is not a function of λ.**

### Limitations

1. **IIT does not hold.** Φ = 0.004–0.011, indistinguishable from a shuffled null;
   σ = 0.42 (subcritical). The system is *not* in a high-Φ regime.
2. **Incomplete controls.** Only GWT-3 has a control that rules out alternative
   explanations; RPT-1 lacks an equal-parameter recurrent baseline, HOT-2 lacks
   confidence-distribution matching, AST-1 lacks an irrelevant-channel control, and
   AE-2 lacks a yoked sham-feedback condition.
3. **Weak specificity.** A sham lesion (random visual content) is as damaging as removal
   (3.05 vs 2.80; hazard 10.20 vs 8.97), so we claim channel *necessity*, not functional
   specificity.
4. **Multiple comparisons.** 55 p-values across the project; 24 survive Benjamini–Hochberg
   at FDR=0.05. The tests are correlated, so this is approximate.
5. **External validity.** A 16×16 grid world is far from any real system, and the Φ–λ
   counter-example is confined to deterministic four-node Boolean networks.
