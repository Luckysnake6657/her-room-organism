# 给她接身体：桥接补丁说明（未应用）

> 这份是**给管理员看的补丁单**，不是已改的代码。`D:\qq-bridge` 在工作区外，
> 需要你点头/给权限才能动，而且它是活系统，改动必须走 verify。

## 目标

她的嘴不变（DSH + 记忆 + 人格 + 语音），只加：

1. **状态**：每轮知道"她现在饿/困/烦/病"
2. **延迟**：回多快由身体算，不由模型演
3. **缺席**：关掉再开，知道过了多久、身体什么样

## 已准备好的东西

- 身体服务：`D:\deepseekharness\lab\cmw-organism\serve.ps1`（端口 3210）
- 客户端：`D:\deepseekharness\lab\dc\deploy\cmw\organism-client.mjs`
  → 复制到 `D:\qq-bridge\src\organism-client.mjs`
- 契约测试：`deploy\cmw\test-client.mjs`（已对着副本跑通：`t=361 delay=8 words=58 days=1`）

## 一键补丁（已验证语法）

```powershell
copy D:\deepseekharness\lab\dc\deploy\cmw\organism-client.mjs D:\qq-bridge\src\organism-client.js
cd D:\deepseekharness\lab\dc\deploy\cmw
node apply-bridge-patch.mjs --check     # 4 处改动都只命中 1 次 + 语法检查
node apply-bridge-patch.mjs --write     # 写回（自动备份 bridge.js.bak-organism）
```

`--write` 之后在 `D:\qq-bridge\config.json` 加：

```json
"organism": { "enabled": true, "stateLine": true, "baseUrl": "http://127.0.0.1:3210" }
```

重启桥接，`npm run verify`。回滚：把 `bridge.js.bak-organism` 拷回去 + `enabled:false`。

`stateLine:false` 可以只留延迟、不注入状态（不用重新打补丁）。

## 函数位置（2026-10-28 只读查到的）

| 位置 | 行号 | 用途 |
|---|---|---|
| `sendWakePromptV2(key, reason)` | 16564 | 拼唤醒提示词 |
| `baseDynamic = wakeLine + … + statusLine + nowPlayingLine` | 16407 | 动态段，状态行加这里 |
| `sendToQQ(key, msg)` | 8845 | 文本发送（单条） |
| `sendBurstToQQ(key, messages, …)` | 8983 | 多气泡发送 |
| `onebotSend(kind, id, message, …)` | 9414 | 底层发送 |

## 补丁（一次只上一处）

### 第 1 步：只加延迟（风险最低）

在私聊消息到达、调用 `sendWakePromptV2` 之前：

```js
if (cfg.organism?.enabled) {
  try { st.organism = await organismForm(cfg.organism.baseUrl, String(key), text); }
  catch { st.organism = null; }
}
```

在 `sendToQQ`（8845）和 `sendBurstToQQ`（8983）真正发送前：

```js
const d = Math.min(Number(st.organism?.delay_s) || 0, 300);
if (d > 0) await sleep(d * 1000);
```

**验收**：`enabled=true` 时发送间隔随状态变；`false` 时与现在逐字一致。
**回滚**：`enabled=false`。

### 第 2 步：加状态注入

在 `sendWakePromptV2` 里，`baseDynamic`（16407）拼好之后：

```js
const organismLine = st.organism ? `【你现在】${st.organism.state}\n` : '';
const prompt = base + organismLine;   // 或并入 baseDynamic 的某个变量
```

只加状态，不加身份；不要写"你是某某"。

**验收**：她的话里开始出现"今天有点累"这类，且不是每轮都有（身体好时不出现）。

### 第 3 步：缺席结算

bridge 启动、连上网关后：

```js
const gapMin = (Date.now() - (cfg.lastSeenAt || Date.now())) / 60000;
if (cfg.organism?.enabled && gapMin > 30) {
  const a = await organismAbsence(cfg.organism.baseUrl, 'owner', gapMin);
  if (a) cfg.pendingOrganismAbsence = a;
}
```

下次唤醒时把 `a.settlement` 和 `a.disclosure` 各注入一次（不重复）。

**验收**：关一晚再开，她第一句会带"你不在的时候……"或结算里的世界事实，并带披露。

## 配置（默认关）

```json
"organism": { "enabled": false, "baseUrl": "http://127.0.0.1:3210" }
```

## 回滚

`cfg.organism.enabled = false` + 重启桥接。身体存档留着，下次开继续。

## 没做的

- 消息文本在 bridge 里存在哪个变量（`st.lastText`? `msg.text`?）要读消息处理段确认，
  上面写的是占位名。
- 群聊不接（只读）。
- 语音不接（身体只影响文本节奏）。

## 顺序

1. 先跑身体 + `test-client.mjs`（已通）
2. 只加"延迟"，verify + 观察一天
3. 再加"状态注入"，verify
4. 最后"缺席结算"
