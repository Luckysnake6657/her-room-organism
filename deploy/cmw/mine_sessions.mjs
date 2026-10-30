// 从多个 DSH home 里挖"她真正发出去的话"。
// 只扫 her 的项目目录（qq-bridge-state-agents），不碰 self-test / 我自己的会话。
// 用法：node mine_sessions.mjs [输出目录]
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';

const OUT = process.argv[2] || 'evidence/p3/cmw_sessions';
const ROOTS = [
  (process.env.QQ_DSH_SESSIONS || 'sessions'),
  (process.env.DSH_SESSIONS || '.dsh/sessions'),
];

function walk(dir, acc = []) {
  let ents;
  try { ents = fs.readdirSync(dir, { withFileTypes: true }); } catch { return acc; }
  for (const e of ents) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, acc);
    else if (e.name.endsWith('.zstd')) acc.push(p);
  }
  return acc;
}

const files = [];
for (const r of ROOTS) {
  for (const f of walk(r)) {
    if (/qq-bridge-state-agents/.test(f)) files.push(f);
  }
}
fs.mkdirSync(OUT, { recursive: true });
const out = fs.createWriteStream(path.join(OUT, 'her_lines.jsonl'), { encoding: 'utf8' });

let sessions = 0, calls = 0, lines = 0;
const seen = new Set();

for (const f of files) {
  let text;
  try { text = zlib.zstdDecompressSync(fs.readFileSync(f)).toString('utf8'); } catch { continue; }
  sessions++;
  for (const l of text.split(/\r?\n/)) {
    if (!l) continue;
    let r; try { r = JSON.parse(l); } catch { continue; }
    if (r.type !== 'tool/call') continue;
    const name = String(r?.data?.name || '');
    if (!/qq_send_message|qq_reply/.test(name)) continue;
    calls++;
    let args;
    try { args = JSON.parse(r.data.arguments); } catch { continue; }
    const msgs = Array.isArray(args?.messages) ? args.messages
      : (typeof args?.text === 'string' ? [args.text] : []);
    for (const m of msgs) {
      const t = String(m || '').trim();
      if (!t || t.length > 300) continue;
      if (seen.has(t)) continue;
      seen.add(t);
      out.write(JSON.stringify({ t: r.time || 0, text: t, key: String(args.key || ''), session: path.basename(path.dirname(f)) }) + '\n');
      lines++;
    }
  }
}
out.end();
console.log(JSON.stringify({ files: files.length, sessions, calls, lines }));
