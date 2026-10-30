# 数据边界（lab-home）

写于 2026-10-27。这份文件回答一个问题：**她存了什么、什么离开这台机器、你怎么去掉它。**

---

## 一、存了什么（明文）

| 路径 | 内容 | 敏感度 |
|---|---|---|
| `memory/events.jsonl` | 每轮的用户原话 + 她的回复（记忆源） | **高**：全部对话内容 |
| `memory/dialogue_ledger.jsonl` | 决策台账：原话、回复、状态、动作 | **高** |
| `state.json` | 内部状态（四驱动 x、信任/芥蒂、轮数） | 中 |
| `transcript.txt` | 可读转录 | **高** |
| `outbox/`、`world/` | 运行产物（笔记/任务/反思） | 低 |

`lab-home/` 已在 `.gitignore` 里，**不会进 git**。

## 二、什么离开这台机器

每轮对话会把 **system 提示词 + 最近 8 轮历史 + 本轮用户输入** 发到
`https://api.deepseek.com`（模型 `deepseek-flash`）。这是生成回复的必要条件。

**不发的东西**：`state.json`、台账、记忆库全文都不整包外发；
记忆只以"检索出的 3 条摘要"形式进入提示词。

## 三、三个出口（CLI）

```powershell
python labhome/talk.py --i-consent          # 首次知情（之后才允许对话）
python labhome/talk.py --export 备份.json    # 导出全部历史为单个 JSON
python labhome/talk.py --purge --yes        # 清除记忆与台账（--keep-state 保留她的状态）
```

首次运行若未知情，会打印数据说明并拒绝进入对话。

## 四、诚实的技术限制

1. **覆盖写不等于物理擦除。** SSD 的磨损均衡会把旧块留在别处，
   `--purge` 是"尽力清除 + 明确告知"，不是安全擦除。真正的保证只能来自全盘加密。
2. **没有做本地加密。** 把密钥放在同一台机器上，是安全剧场。
   要真做，应接操作系统的凭据存储（Windows DPAPI / macOS Keychain）——
   那是另一件事，且会引入"密钥丢了记忆就没了"的新风险。
3. **外部 API 那一端不在我们控制内。** 这是使用云端模型的固有代价；
   要彻底解决只能换本地模型（`models/qwen2.5-1.5b-instruct` 已有，质量明显下降）。
4. **导出是明文 JSON**，导出之后的安全责任在使用者。

## 五、自检

`labhome/selfcheck.py` 第 [18] 组覆盖：清点、导出完整性、默认未同意、同意后标记、清除生效。
