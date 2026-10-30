// 桥接补丁 v2：只对 owner 私聊，把 native 的状态/处境/记忆注入提示词，发送前按延迟等。
// --check 只验语法；--write 写回（自动备份）。
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const SRC = (process.env.QQ_BRIDGE_ROOT || '.') + '/src/bridge.js';
const MODE = process.argv.includes('--write') ? 'write'
  : process.argv.includes('--check') ? 'check' : 'diff';
let code = fs.readFileSync(SRC, 'utf8');
const hadCRLF = code.includes('\r\n');
code = code.replace(/\r\n/g, '\n');
const changes = [];

function rep(name, from, to) {
  const n = code.split(from).length - 1;
  if (n !== 1) throw new Error(`${name}: 命中 ${n} 次`);
  code = code.replace(from, to);
  changes.push(name);
}

rep('import-helper',
  "import { parseMessageList } from './message-list.js';",
  "import { parseMessageList } from './message-list.js';\n"
  + "const organismByKey = new Map();\n"
  + "async function organismContext(text) {\n"
  + "  const base = String(cfg.organism?.baseUrl || 'http://127.0.0.1:3210').replace(/\\/$/, '');\n"
  + "  const r = await fetch(base + '/context', { method: 'POST', headers: { 'content-type': 'application/json' },\n"
  + "    body: JSON.stringify({ text: String(text || '') }), signal: AbortSignal.timeout(2000) });\n"
  + "  if (!r.ok) return null;\n"
  + "  return await r.json();\n"
  + "}");

rep('context-call',
  "    if (!isSessionAllowedInCurrentMode(key)) {\n"
  + "      log(`[reserved2] 跳过唤醒 ${key}（${reason}）：会话已不在当前模式允许范围内`);\n"
  + "      return;\n"
  + "    }\n"
  + "    const st = getSocialV2State(key);",
  "    if (!isSessionAllowedInCurrentMode(key)) {\n"
  + "      log(`[reserved2] 跳过唤醒 ${key}（${reason}）：会话已不在当前模式允许范围内`);\n"
  + "      return;\n"
  + "    }\n"
  + "    const st = getSocialV2State(key);\n"
  + "    if (cfg.organism?.enabled && key === 'private:' + String(cfg.ownerQQ ?? '')) {\n"
  + "      try {\n"
  + "        const last = (st.recentMessages || []).filter((m) => !m.isSelf && m.text).slice(-1)[0];\n"
  + "        const o = await organismContext(last ? last.text : '');\n"
  + "        if (o) { o.__delayed = false; organismByKey.set(key, o); }\n"
  + "      } catch { organismByKey.delete(key); }\n"
  + "    }");

rep('inject',
  "    const base = baseStable + baseDynamic;",
  "    const __o = organismByKey.get(key);\n"
  + "    let __oLine = '';\n"
  + "    if (__o) {\n"
  + "      __oLine += `【你现在】${__o.state}\\n`;\n"
  + "      if (__o.mood) __oLine += `【底色】${__o.mood}\\n`;\n"
  + "      const b = __o.bdi || {};\n"
  + "      if (b.activity) __oLine += `【他在】${b.activity}\\n`;\n"
  + "      if (b.mood) __oLine += `【他此刻】${b.mood}\\n`;\n"
  + "      if (b.belief) __oLine += `【他以为】${b.belief}\\n`;\n"
  + "      if (Array.isArray(__o.memories) && __o.memories.length) __oLine += '【你记得的事】\\n- ' + __o.memories.join('\\n- ') + '\\n';\n"
  + "    }\n"
  + "    const base = baseStable + baseDynamic + __oLine;");

rep('delay',
  "  function sendToQQ(key, msg) {\n"
  + "    const assertSendAllowed = captureSendGuard(key);\n"
  + "    const safeMsg = redactKnownTokensOnly(msg);\n"
  + "    const [kind, id] = key.split(':');\n"
  + "    const parts = splitForQQ(safeMsg);\n"
  + "    for (const part of parts) {\n"
  + "      sendChain = sendChain\n"
  + "        .then(async () => {\n"
  + "          assertSendAllowed();",
  "  function sendToQQ(key, msg) {\n"
  + "    const assertSendAllowed = captureSendGuard(key);\n"
  + "    const safeMsg = redactKnownTokensOnly(msg);\n"
  + "    const [kind, id] = key.split(':');\n"
  + "    const parts = splitForQQ(safeMsg);\n"
  + "    for (const part of parts) {\n"
  + "      sendChain = sendChain\n"
  + "        .then(async () => {\n"
  + "          const __o = organismByKey.get(key);\n"
  + "          if (__o && !__o.__delayed) {\n"
  + "            __o.__delayed = true;\n"
  + "            const d = Math.min(Number(__o.delay_s) || 0, 300);\n"
  + "            if (d > 0) await sleep(d * 1000);\n"
  + "          }\n"
  + "          assertSendAllowed();");

console.log('changes:', changes.join(','));
if (hadCRLF) code = code.replace(/\n/g, '\r\n');
if (MODE === 'check') {
  const tmp = path.join(process.cwd(), '_bridge_v2_check.mjs');
  fs.writeFileSync(tmp, code, 'utf8');
  try { execFileSync(process.execPath, ['--check', tmp], { stdio: 'inherit' }); console.log('syntax OK'); }
  finally { fs.unlinkSync(tmp); }
} else if (MODE === 'write') {
  fs.copyFileSync(SRC, SRC + '.bak-v2');
  fs.writeFileSync(SRC, code, 'utf8');
  console.log('written; backup at', SRC + '.bak-v2');
} else {
  console.log('dry');
}
