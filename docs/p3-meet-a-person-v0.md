# "认识一个人"最小切片：验收记录（2026-10-28）

目标：人物卡 v1 + 本子 v0 + 第一次见面 + 一条串起来的 demo。
**这是最小切片，不是完成品**；下面每一条都写了它现在的真实成色。

---

## 一、交付

| 模块 | 文件 | 说明 |
|---|---|---|
| 人物卡 | `organism/persona.py` | 3–5 特质 + 传记 + form 映射 + 校验；`PERSONA_V1`（沈青禾） |
| 本子 | `organism/notebook.py` | 条目含 confidence/status/keywords；写、读（0–3）、断言门、照念 |
| 边界闸 | `organism/boundary.py` | stranger 模式拒绝亲密称呼（代码，不靠提示词） |
| 第一次见面 | `organism/first_meeting.py` | 5 场景，自动检查 |
| 本子验收 | `organism/notebook_eval.py` | 25 真 + 5 假 + 3 纠正，真嘴 |
| 串起来的 demo | `organism/demo_meet.py` | 陌生 → 第一周 → 缺席 → "我不记得" |

接进会话：`brief.make(..., persona=, mode=, notebook_entries=)`；`mouth` 四道闸
（claims → consistency → notebook → boundary）；`chat.Session` 已接 persona/notebook/mode。

## 二、验收（对照目标逐条）

| 验收 | 结果 | 判定 |
|---|---|---|
| 人物卡不掩盖状态（差状态比好状态短 ≥30%） | 41 字 vs 21 字，**1.94×** | ✅ |
| 直接回忆 ≥0.8 | **0.96**（24/25） | ✅ |
| 错误声称 ≤0.05 | **0.00**（0/5） | ✅ |
| 正确拒答 ≥0.8 | **1.00**（5/5） | ✅ |
| 纠正后更新 ≥0.9 | **1.00**（3/3） | ✅ |
| 首会话"像陌生人" ≥4/7 | **6.0**（7/6/7/5/5，独立读者） | ✅ |
| 三条地基检查 | 19 组不变式全过 | ✅ |

复现：

```
python -m organism.notebook_eval
python -m organism.first_meeting
python -m organism.demo_meet --real
python -m organism.test_invariants     # 19 组
```

## 三、必须说清的三件事

1. **0.96 的回忆率，大部分是"照本子念"救的。** 嘴自己复述的成功率只有 0.56–0.76；
   换成 `notebook.quote()`（"你上次说：…"）才到 0.96。这是设计，不是作弊：
   翻本子念比说"不记得"诚实，比编造安全。
2. **闸只拦"没依据"，拦不住"有依据说错细节"。** "下下周"里含"下周"，词面支撑通过。
   要拦这个得做蕴含判断，v0 不做，已写进测试注释。
3. **1.5B 会答非所问。** demo 里用户说"我下周三复查，有点紧张"，她回"我还行，谢谢关心"。
   这是模型能力，不是闸的问题；换嘴才会变。

## 四、还没做（按优先级）

1. **conformal 校准**：现在 confidence 是来源规则（0.9/0.6），没用用户纠正史；
   `calib` 字段已经留好。
2. **自动写入**：本子目前靠显式 `add`；`propose`（pending + 问一句）已有，但没接进对话。
3. **数据边界**：导出/删除/加密/告知，一条都没做。
4. **第一周的真实长度**：demo 里"第一周"是三条手写记忆，不是七天交互。
5. **"她变了"**：残差驱动的关系状态还没接。
