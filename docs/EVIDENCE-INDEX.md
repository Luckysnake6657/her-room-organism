# 实验日志索引

仓库里的 `evidence/` 是各项实验的原始输出；`docs/` 是预注册、结果与方法说明。
**不含**她的私人对话、角色卡、记忆与任何 API key。

## 目录

### `evidence/p0/` 身体与消融
六状态（能量/睡眠债/应激/免疫/孤独/昼夜错位）是否承重。
- 消融结果、生存曲线、逐日记录。
- 判据：冻结任一变量，行为/生存显著退化。

### `evidence/p0b/` 威胁密度
std vs dense 两种世界，测应激是否只在密集威胁下承重。
- `stress→sleep 1.56×`、`stress→immune 2.22×`、总体 `3.01×`。

### `evidence/p0_dev/`、`p0_dev2/`
P0 的开发期草稿与中间结果（保留以便追溯，不作为最终证据）。

### `evidence/p1/` 离线与连续性
- 离线补算 vs 连续运行逐位对比。
- 长命（30/90 天）与时间尺度。

### `evidence/p2/` 形式通道
延迟/字数/主动是否由身体算出；边界与单调性。

### `evidence/three_condition/` 可读性 3c
三种呈现（完整/只内容/只形式）× 多段对话；判读者打分。
- 结果：ρ = 0.83 / 0.93 / 0.88（均值 0.88，sd 0.04）。
- 已知缺陷：C 条件含"隔了 X 秒"，秒数泄漏状态，判据 3 不通过。

### `evidence/story/` 成长剧本
12 天设计输入：重复事实/行为、正面互动、失联。
- 巩固第 3 天跨线；习惯第 2–3 天；U 失联爬升、回来回落。

### 根目录探针
- `ablation*.jsonl`：消融逐日记录
- `phi*.json`、`gwt*.json`、`hot*.json`、`criticality.json`：整合/广播/高阶表征等探针（探索性，部分阴性）
- `probe_*.json`：状态探针与留出检验
- `blind_review*.json`：盲评分数
- `contract_tests.json`：契约测试输出
- `research_batch.json`：威胁密度 + words_base
- `retrieval_compare.json`：字面 vs 向量检索（阴性：18% vs 54%）
- `u_recovery.json`、`ask_slow_param.txt`：U 恢复与慢参数
- `mouth_eval*.json`、`notebook_eval.json`、`longitudinal.json`：嘴/记忆/纵向评测
- `audit_met.md`、`butlin_*`、`manipulation_audit.json`：外部框架对照与操纵审计

## 复现

```bash
python -m organism.test_invariants    # 45 组不变量
python -m organism.contract_tests     # 50 条契约
python -m organism.research_batch     # 威胁密度 + words_base
python -m organism.retrieval_compare  # 字面 vs 向量
python -m organism.growth_eval        # 阶跃/饱和/递减/指数
python -m organism.u_sim              # U 半衰期敏感性
```

## 说明

- 部分探针是探索性的，结果阴性也保留；
- 模拟实验的间隔/阈值在对应 docs 里标明，不当作真实世界证据；
- 隐私相关的原始对话已从发布包中排除。
