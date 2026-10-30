# 效价通路失效审计

日期：2026-10-26（P0 复核时发现）
影响范围：`src/affect.py` 的整条通路（不是它本身的错，是调用时机）；所有引用 "valence_off" 的结论
守卫：`experiments/check_affect.py`

---

## 0. 一句话

**`valence` 从项目开始到 2026-10-26 中午一直是 0.0，从来没动过。**
所有“效价三版设计全阴性”的结论，实际测的是 `intero_precision` 的调制，不是效价。

---

## 1. 怎么发现的

P0（无奖励探索）第一次试跑就出现怪事：`baseline` 与 `valence_off` 的
4 seeds × 400 步指标**完全一致**——已知格子 0.329、走过 0.166、危险 1.8、奖励 −0.007。

逐 tick 比对动作序列，完全相同。于是去看 trace 里的效价：

```
valence min/max = 0.0 / 0.0
```

换到觅食任务（默认 v3 配置）也一样：700 步里 arousal 最高到 0.57、能量从 1.0 掉到 0.665，
`valence` 仍然恒等于 0.0。

---

## 2. 根因（一行）

`sim.py` 在 tick 开头这样算效价：

```python
prev_body = self.body.state()                      # tick 开头的快照
aff = self.affect.compute(self.prev_body_state, prev_body)
```

而 `self.prev_body_state` 是**上一 tick 末尾**（`body.consume()` 之后）赋的值：

```python
self.prev_body_state = self.body.state()           # tick 末尾
```

两个快照在 tick 开头必然**完全相等** → `de = di = dt = df = 0` → `delta = 0` →
`valence = 0.85 × valence + 0.15 × 0` → 永远停在 0。

`Affect.compute()` 本身没问题；错的是传进去的两个参数是同一时刻的身体状态。

---

## 3. 后果：哪些结论要改

`valence_off` 分支把 `global_modulation` 全部设为默认值。因为 baseline 的 valence 恒为 0，
它的默认值也是 `policy_temp = 1.0`、`risk_aversion = 1.0`，所以两边**唯一的真实差别**是：

| 通道 | baseline（修复前） | valence_off | 有差别？ |
|---|---|---|---|
| policy_temp | 1 − 0.2×0 = 1.0 | 1.0 | 否 |
| risk_aversion | 1 + 0 = 1.0 | 1.0 | 否 |
| intero_precision | 1 + 0.5×arousal | 1.0 | **是** |
| ws_capacity_delta | 0 | 0 | 否 |

**也就是说：所谓“效价消融”实际是“内感受精度调制消融”。**
HANDOFF §6 第 1–3 行（效价三版设计全阴性）应改读为“内感受精度调制阴性”；
`docs/final-report.md` 里讲效价失败的地方都要加注。

好消息：`butlin.py` 里没有引用 valence（已 grep），14 项评分不直接受影响。

---

## 4. 修复

效价改为**在 tick 末尾积分、下一 tick 生效**（语义不变：效价是状态整体的慢积分，只是终于在对变化积分）：

```python
# tick 末尾：身体已经变化完
self.aff = self.affect.compute(prev_body, self.body.state())
```

tick 开头改用 `aff = self.aff`；`valence_off` 分支不变（仍然把调制压平）。
初始化给中性值，避免第一步没有历史。

---

## 5. 修复后的证据

| 任务 | baseline 效价范围 | valence_off |
|---|---|---|
| 觅食 v3（700 步，seed 0） | [−0.43, +0.50] | 恒 0.0 |
| 探索 P0（600 步，seed 0） | [−0.34, 0.00] | 恒 0.0 |

守卫脚本输出：foraging 有正有负、explore 不全为 0、valence_off 恒 0、
baseline 与 valence_off 的动作序列在 600 步里有 324 步不同 → 通路接上了。

EI v2 在修复后重算（60 seeds）：baseline 2.289、workspace_off 2.404、
Δ = −0.114，95%CI [−0.185, −0.035] —— **结论不变**（竞争不抬高 EI）。

---

## 6. 守卫

`experiments/check_affect.py`，退出码即结论：

1. 觅食 baseline 的效价有正有负（|v| > 0.05）
2. 探索 baseline 的效价不全为 0（|v| > 0.01）
3. valence_off 恒为 0（消融本身有效）
4. baseline 与 valence_off 的动作序列不完全相同（消融真的接上了）

以后只要动 `sim.py` 的 tick 顺序，就必须跑它。

---

## 7. 教训

和 `docs/ei-results.md` 那次是同一个形状：**输入/定义域错了，数值照样出得来。**

- EI v1：状态编码依赖被消融的机制 → 0.216 是填充算出来的
- 效价：两个快照相同 → valence ≡ 0，消融变成另一个消融

所以每个“阴性”都要配一个 **manipulation check**：被操纵的那个量，真的动了吗？
只看组间 p 值会把这个错误藏起来——因为两边都恒为 0，p 自然是 1，看起来像“没有效应”。
