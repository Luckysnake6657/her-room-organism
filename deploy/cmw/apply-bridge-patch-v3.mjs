// 桥接补丁 v3：主动开口交给 native。
// 在 proactiveCheck 唤醒时先问 native /proactive；有文本就直接发，不再唤醒 DSH。
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

rep('proactive-helper',
  "async function organismContext(text) {",
  "async function organismProactive() {\n"
  + "  const base = String(cfg.organism?.baseUrl || 'http://127.0.0.1:3210').replace(/\\/$/, '');\n"
  + "  const r = await fetch(base + '/proactive', { method: 'POST', headers: { 'content-type': 'application/json' },\n"
  + "    body: '{}', signal: AbortSignal.timeout(15000) });\n"
  + "  if (!r.ok) return null;\n"
  + "  const d = await r.json();\n"
  + "  return d && d.text ? d : null;\n"
  + "}\n"
  + "async function organismContext(text) {");

rep('proactive-branch',
  "    if (cfg.organism?.enabled && key === 'private:' + String(cfg.ownerQQ ?? '')) {\n"
  + "      try {\n"
  + "        const last = (st.recentMessages || []).filter((m) => !m.isSelf && m.text).slice(-1)[0];",
  "    if (cfg.organism?.enabled && key === 'private:' + String(cfg.ownerQQ ?? '') && reason === 'proactiveCheck') {\n"
  + "      try {\n"
  + "        const p = await organismProactive();\n"
  + "        if (p && p.text) {\n"
  + "          log(`[organism] 主动 ${key}: ${p.text}`);\n"
  + "          sendToQQ(key, p.text);\n"
  + "          return;\n"
  + "        }\n"
  + "      } catch {}\n"
  + "    }\n"
  + "    if (cfg.organism?.enabled && key === 'private:' + String(cfg.ownerQQ ?? '')) {\n"
  + "      try {\n"
  + "        const last = (st.recentMessages || []).filter((m) => !m.isSelf && m.text).slice(-1)[0];");

console.log('changes:', changes.join(','));
if (hadCRLF) code = code.replace(/\n/g, '\r\n');
if (MODE === 'check') {
  const tmp = path.join(process.cwd(), '_bridge_v3_check.mjs');
  fs.writeFileSync(tmp, code, 'utf8');
  try { execFileSync(process.execPath, ['--check', tmp], { stdio: 'inherit' }); console.log('syntax OK'); }
  finally { fs.unlinkSync(tmp); }
} else if (MODE === 'write') {
  fs.copyFileSync(SRC, SRC + '.bak-v3');
  fs.writeFileSync(SRC, code, 'utf8');
  console.log('written; backup at', SRC + '.bak-v3');
} else {
  console.log('dry');
}
