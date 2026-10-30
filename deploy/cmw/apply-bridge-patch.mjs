// 桥接补丁器：读 D:\qq-bridge\src\bridge.js，在内存里打三处补丁。
//   node apply-bridge-patch.mjs --check    只做语法检查（写临时文件到当前目录）
//   node apply-bridge-patch.mjs --write    写回原文件（需要写权限）
//   node apply-bridge-patch.mjs --diff     打印改动摘要，不写
import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const SRC = process.argv.find((a) => a.startsWith('--src='))?.slice(6)
  || (process.env.QQ_BRIDGE_ROOT || '.') + '/src/bridge.js';
const MODE = process.argv.includes('--write') ? 'write'
  : process.argv.includes('--check') ? 'check' : 'diff';

let code = fs.readFileSync(SRC, 'utf8');
const hadCRLF = code.includes('\r\n');
code = code.replace(/\r\n/g, '\n');
const changes = [];

function replaceOnce(name, from, to) {
  const n = code.split(from).length - 1;
  if (n !== 1) throw new Error(`${name}: 期望命中 1 次，实际 ${n} 次`);
  code = code.replace(from, to);
  changes.push(name);
}

// 1) import + 模块级 map
replaceOnce(
  'import',
  "import { mdToPlain, splitForQQ } from './md-to-plain.js';",
  "import { mdToPlain, splitForQQ } from './md-to-plain.js';\n"
    + "import * as organismClient from './organism-client.js';\n"
    + "const organismByKey = new Map();"
);

// 2) sendWakePromptV2：取形式，挂到 map
replaceOnce(
  'form-call',
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
    + "    let organism = null;\n"
    + "    if (cfg.organism?.enabled && key === 'private:' + String(cfg.ownerQQ ?? '')) {\n"
    + "      try {\n"
    + "        organism = await organismClient.form(cfg.organism.baseUrl, key, '');\n"
    + "        if (organism) { organism.__delayed = false; organismByKey.set(key, organism); }\n"
    + "      } catch { organism = null; }\n"
    + "    }"
);

// 3) 状态行进提示词
replaceOnce(
  'state-line',
  "    const base = baseStable + baseDynamic;",
  "    const __org = organismByKey.get(key);\n"
    + "    const organismLine = (__org && cfg.organism?.stateLine !== false)\n"
    + "      ? `【你现在】${__org.state}\\n` : '';\n"
    + "    const base = baseStable + baseDynamic + organismLine;"
);

// 4) 发送前按身体延迟（每条消息只等一次）
replaceOnce(
  'send-delay',
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
    + "          const org = organismByKey.get(key);\n"
    + "          if (org && !org.__delayed) {\n"
    + "            org.__delayed = true;\n"
    + "            const d = Math.min(Number(org.delay_s) || 0, 300);\n"
    + "            if (d > 0) await sleep(d * 1000);\n"
    + "          }\n"
    + "          assertSendAllowed();"
);

console.log('changes:', changes.join(', '));
if (hadCRLF) code = code.replace(/\n/g, '\r\n');

if (MODE === 'check') {
  const tmp = path.join(process.cwd(), '_bridge_patched_check.mjs');
  fs.writeFileSync(tmp, code, 'utf8');
  try {
    execFileSync(process.execPath, ['--check', tmp], { stdio: 'inherit' });
    console.log('syntax OK:', tmp);
  } finally {
    fs.unlinkSync(tmp);
  }
} else if (MODE === 'write') {
  const bak = SRC + '.bak-organism';
  fs.copyFileSync(SRC, bak);
  fs.writeFileSync(SRC, code, 'utf8');
  console.log('written; backup at', bak);
} else {
  console.log('dry run only; add --check or --write');
}
