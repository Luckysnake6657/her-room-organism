# 文献、论文、项目地图 —— 为「可能性」方案配的弹药

查于 2026-10-26/27。**我只读了标题与摘要，没有逐篇读全文**，凡未核实的都按"只看过摘要"标注。
每一条都写了：一句话内容 / 对我们哪个阶段有用 / 怎么用。

配套方案：`docs/possibility-plan.md`（阶段 0–4）。

---

## 一、最重要的一条：这件事已经有一个专门的会场

**AAAI 2026 Spring Symposium — Machine Consciousness: Integrating Theory, Technology, and Philosophy**
2026 年 4 月 7–9 日，Burlingame。论文集 28 篇：
<https://ojs.aaai.org/index.php/AAAI-SS/issue/view/734>

**为什么这条最重要**：用户要的"学术上被认为有可能"，落点就在这里。这不是 NeurIPS 那种尺度的会场，
是一个小而专、主题完全对口的 symposium——**下一个 session 就是我们该投的地方**。
而且这 28 篇等于一份现成的"同行都在做什么"清单（下面按类拆）。

**风险**：这个会场说明赛道上已经有人，且不止一队。

---

## 二、方法：怎么测（对应方案阶段 0/2/4）

| 文献 | 一句话 | 怎么用 |
|---|---|---|
| Butlin et al. 2023, *Consciousness in AI: Insights from the Science of Consciousness*，arXiv:2308.08708 <https://arxiv.org/abs/2308.08708> | 14 项 indicator properties 的原始来源；明确"没有技术障碍，但现有系统都没过" | 我们的记分卡就是它。**引用时必须引"indicator 是提升/降低可信度的证据，不是判决"这一定位** |
| Long et al. 2024, *Taking AI Welfare Seriously*，arXiv:2411.00986 <https://ar5iv.labs.arxiv.org/html/2411.00986v1> | 把"AI 福利"变成概率化、多理论的评估问题 | 我们"贝叶斯合成"那节的正当性来源；但也是它提醒了独立性问题 |
| Hughes & Nguyen 2026, *Triangulating Evidence for Machine Consciousness Claims: A Validity-Centered Stack of Behavioral Batteries, Mechanistic Indicators, Perturbation Tests, and Credence Reporting*，AAAI-SS 42552 <https://ojs.aaai.org/index.php/AAAI-SS/article/view/42552> | **和我们的方法论几乎同一张图纸**：行为电池 + 机制指标 + 扰动测试 + 可信度报告 | 必读。是"相关工作"里最难写的一段，因为它太像我们 |
| Niazi 2026, *Beyond mimicry: mPCAB*，Front. AI 8:1686752 <https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2025.1686752/full> | **Machine Perturbational Complexity & Agency Battery**：扰动复杂度 + 全局工作空间 + 规范内化 + 能动性，跨基底 | 说明"跨学科电池"不是我们首创；但它是框架/试点，不是带预注册关闭的实测。我们的位置是**执行**，不是**构想** |
| Rahbar 2026, *The Ignition Index*，arXiv:2608.05160 <https://arxiv.org/abs/2608.05160> | 把 GWT 的 "全或无点燃" 做成可算标量：逐层线性探针准确率对信号强度拟合 sigmoid，取陡度；**带 shuffled-label 对照（9.6 倍选择性）**；代码开源 <https://github.com/saman-rahbar/ignition-index> | **阶段 2/4 直接用**。我们的 ignition 方案原来只写"同步度阶跃"，这个给了一个已验证、带对照的操作化 |
| Cogitate Consortium 2025, *Adversarial testing of global neuronal workspace and integrated information theories of consciousness*，Nature <https://www.nature.com/articles/s41586-025-08888-1> | IIT 与 GNWT 的对抗性合作实验，两边都只被部分支持 | "跨学科标记互相检验"的顶级先例。写未来工作时的模板 |
| Casali et al. 2013, *A theoretically based index of consciousness independent of sensory processing and behavior*，Sci Transl Med | PCI 的原始来源（清醒高、麻醉低、不依赖行为） | PCI 的临床合法性就靠这一篇（此项未在本次检索中核对链接） |
| *Emergence and Causality in Complex Systems: A Survey of Causal Emergence*，Entropy 2024 <https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10887681/> | 因果涌现的综述，含 EI 的各种定义与批评 | 我们 EI 那部分的方法学依据；也提醒"EI 依赖粗粒化"不是我们独有的发现 |
| PyPhi 文档（IIT 4.0 demo） <https://pyphi.readthedocs.io/en/latest/examples/IIT_4.0_demo.html> | 参考实现；`formalism="IIT_3_0"` 才与 1.x 可比 | 阶段 0 直接用；我们已经踩过这个坑 |

---

## 三、架构：怎么做（对应方案阶段 0/1/2）

| 文献 | 一句话 | 怎么用 |
|---|---|---|
| VanRullen & Kanai 2021, *Deep learning and the Global Workspace Theory*，Trends Cogn Sci | 把 GWT 落到深度学习架构上的路线图（共享 latent space、竞争、广播） | 阶段 0 的核设计依据 |
| **Sanyal 2026, *ReCoN-Ipsundrum*，AAAI-SS 42565 / arXiv:2602.23232** <https://arxiv.org/abs/2602.23232> | **最接近我们的先行工作**：可检查 agent + 递归持续环 + affect 代理 + 三种变体固定参数消融 + **在回合内做因果 lesion** + 明确"不主张有意识" | 必读，且要**逐条对比**：它有 lesion 但我们有 sham；它有 affect 但它没有 Φ；我们有 Φ⊥λ 反例。代码 <https://github.com/xcellect/recips> |
| *Testing Components of the Attention Schema Theory in Artificial Neural Networks*，arXiv:2411.00983 <https://arxiv.org/abs/2411.00983> | AST 在 ANN 里的可操作化 | AST-1 那一项的补强 |
| Safron et al. 2026, *Integrated World Modeling Theory (IWMT) and the Human Consciousness Hypothesis*，AAAI-SS 42564 | 把预测处理 + GNW + IIT 合成一体的理论框架 | 理论章的可选骨架 |
| Vieira & Gabora 2026, *Autocatalytic Constraint Closure as an Organizational Principle for Machine Consciousness*，AAAI-SS 42568 | 用"自催化约束闭合"（自组织/生命起源的判据）当机器意识的组织原则 | 跨学科的另一条腿；可作为"不可分解性"的替代表述 |
| **Bennett 2026, *A Mind Cannot Be Smeared Across Time* / *No Selves, No Consciousness*，AAAI-SS 42545 / 42546** | 主张心智不能"抹在时间上"、没有自我就没有意识 | **直接支持产品那条"连续性不是可配置项"**：把"记忆不可清零"从产品原则升格为理论主张 |
| **Hughes & Nguyen 2026, *The Hard Part Is ∆: Value-Conflict Adjudication as an Architectural Bridge Between Alignment and Machine Consciousness*，AAAI-SS 42551** <https://ojs.aaai.org/index.php/AAAI-SS/article/view/42551> | 标题即主张：**价值冲突的裁决**是"对齐"与"机器意识"之间的架构桥梁 | ⚠️ **最需要优先读的一篇**。我们的"冲突→整合"假设可能已被它提出。见 §六 的新颖性审计 |

---

## 四、身份、关系、产品侧（对应产品轨 + 阶段 3）

| 文献 | 一句话 | 怎么用 |
|---|---|---|
| Perrier & Bennett 2026, *Time, Identity and Consciousness in Language Model Agents*，AAAI-SS 42561 / arXiv:2603.09043 | LLM agent 的同一性/时间性问题 | 陪伴栈上"她是不是同一个谁"的理论依据 |
| LaPosta 2026, *Echo Systems and the Consequence Boundary: A Runnable Delegation Gate for High-Rapport AI Without Assuming Machine Consciousness*，AAAI-SS 42554 | 高亲密度的 AI 如何在不主张意识的前提下设"后果边界" | **产品红线的现成框架**（不报复、不威胁离开那条线） |
| Mikeda 2026, *When Should We Protect AI? A Precautionary Framework for Consciousness Uncertainty*，AAAI-SS 42555 | 在"不确定它有没有意识"时该给什么保护 | 披露/伦理章的骨架 |
| *From Answers to Relationships: Dual Digital Twins for Well-Being-Oriented Face-to-Face Service*，AAAI-SS 42611 | 从"给答案"转向"建关系"的落地设计 | 产品形态参考 |
| *Identity Masks and Coherence Circles: Geometric Interfaces for Interacting with Latent Dynamical Systems*，AAAI-SS 42562 | 用几何界面维持潜空间动力学的一致性 | "人格连续性"的工程手段 |
| *Beyond Anthropocentric Bias: A Species-Agnostic Framework for Evaluating Behavioural Markers of Sentience in AI Systems*，Zenodo <https://zenodo.org/records/21162193> | 物种无关的 sentience 行为标记框架 | 避免"只按人类标记打分"的批评 |
| *Exploring Consciousness in LLMs: A Systematic Survey*，arXiv:2505.19806 <https://export.arxiv.org/abs/2505.19806> | LLM 意识研究的综述（理论/实现/前沿风险） | 交代"为什么我们不把 LLM 当内核"时的引用源 |

---

## 五、开源项目与代码

| 项目 | 用途 |
|---|---|
| <https://github.com/saman-rahbar/ignition-index> | Ignition Index 参考实现，带 shuffled-label 对照 |
| <https://github.com/xcellect/recips> | ReCoN-Ipsundrum，含 lesion 与全部 assay 代码 |
| <https://pyphi.readthedocs.io/> | PyPhi（我们已经在用 1.2 与 2.0rc4 双份） |
| <https://github.com/Preponderous-Software/artificial-consciousness-simulation-framework> | 一个"涌现属性"仿真框架，成熟度低，只作对照看 |

---

## 六、新颖性审计（诚实版）

这是这份地图最该看的一节。**框架层面，我们能想到的东西基本都有人提过**：

| 我们想做的事 | 已有先例 | 我们还能主张什么 |
|---|---|---|
| 跨学科标记电池（PCI/ignition/Φ/meta-d′/λ/因果涌现） | Niazi 的 mPCAB 已经把四件套做成 battery | **不是"首创电池"，是"首个带预注册关闭与 sham 对照的实测"** |
| 带 sham / lesion 的机制证据 | ReCoN-Ipsundrum、Triangulating Evidence | **只多了"公开失败清单"这一条**——但这条恰好最重要 |
| 价值冲突 → 整合 | Hughes & Nguyen 的 *The Hard Part Is ∆* | 可能被抢。要么引用它并做"实测"，要么放弃这个提法 |
| Φ 与 λ 解耦 | 因果涌现综述里可能有近似主张 | 需要先做一次针对性检索，确认"同 λ 下 Φ 差 10 倍"是否已被报告 |
| 陪伴系统上的 Butlin 评测 | 未见 | **这是目前最干净的空位**：把 14 项测在一个真实部署的陪伴栈上，带 sham |
| 一个可审计的人格内核（会错、会外溢） | 未见同类工程报告 | 产品轨的真空位 |

**结论**：我们的位置不在"想法新"，在**"敢把对照和失败摆出来，并且真的在一个活系统上测"**。
这两件事在文献里都很稀缺——因为难，而且不讨喜。

---

## 七、建议阅读顺序（按 ROI，不按重要性）

1. **Hughes & Nguyen, *The Hard Part Is ∆***（AAAI-SS 42551）—— 先确认我们的核心新假设有没有被抢
2. **Sanyal, *ReCoN-Ipsundrum***（arXiv:2602.23232）—— 最近的一篇同类工程，逐条对比
3. **Rahbar, *The Ignition Index***（arXiv:2608.05160）—— 直接可用的操作化
4. **Hughes & Nguyen, *Triangulating Evidence***（AAAI-SS 42552）—— 方法论撞车最严重的一篇
5. **Bennett, *No Selves, No Consciousness***（AAAI-SS 42546）—— 产品那条"连续性"的理论靠山
6. 其余按需

---

## 八、下一步的文献动作

- [ ] 把 42551 与 42552 的全文拿到（AAAI OJS 现在返回 503，可等几天或用学校/机构代理）
- [ ] 做一次针对性检索：`phi AND lambda AND independence AND boolean network`，确认 Φ⊥λ 的新颖性
- [ ] 记下 AAAI Spring Symposium 2027 的征稿时间（通常在上一年的秋冬）
