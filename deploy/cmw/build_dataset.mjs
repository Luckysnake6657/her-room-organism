// 把她的会话拆成 (完整上下文 → 她的回复) 对，供微调/检索用。
// 上下文 = 她那一轮实际收到的 user/message（含记忆/交接/状态）；
// 回复 = 她那轮通过 qq_send_message 真正发出去的话（多气泡合并）。
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';
import crypto from 'node:crypto';

const ROOTS = [(process.env.QQ_DSH_SESSIONS || 'sessions'), (process.env.DSH_SESSIONS || '.dsh/sessions')];
const OUT = 'evidence/p3/cmw_dataset';
const MAX_CTX = 3000;

function walk(dir, acc = []) {
  let ents; try { ents = fs.readdirSync(dir, { withFileTypes: true }); } catch { return acc; }
  for (const e of ents) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, acc);
    else if (p.endsWith('.zstd') && /qq-bridge-state-agents/.test(p)) acc.push(p);
  }
  return acc;
}

function textOf(content) {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) {
    return content.filter((c) => c && (c.type === 'text' || c.text)).map((c) => String(c.text || '')).join('\n');
  }
  return '';
}

const files = ROOTS.flatMap((r) => walk(r));
fs.mkdirSync(OUT, { recursive: true });
const out = fs.createWriteStream(path.join(OUT, 'pairs.jsonl'), { encoding: 'utf8' });
const seen = new Set();
let pairs = 0, sessions = 0;

for (const f of files) {
  let text;
  try { text = zlib.zstdDecompressSync(fs.readFileSync(f)).toString('utf8'); } catch { continue; }
  sessions++;
  let lastUser = '';
  let replies = [];
  const flush = () => {
    const ctx = lastUser.slice(-MAX_CTX).trim();
    const reply = replies.join('').trim();
    replies = [];
    if (!ctx || !reply || reply.length > 300) return;
    const h = crypto.createHash('sha1').update(ctx + '\u0000' + reply).digest('hex');
    if (seen.has(h)) return;
    seen.add(h);
    out.write(JSON.stringify({ context: ctx, reply, n: reply.length }) + '\n');
    pairs++;
  };
  for (const l of text.split(/\r?\n/)) {
    if (!l) continue;
    let r; try { r = JSON.parse(l); } catch { continue; }
    if (r.type === 'user/message') {
      if (lastUser) flush();
      lastUser = textOf(r?.data?.content);
      replies = [];
    } else if (r.type === 'tool/call' && /qq_send_message|qq_reply/.test(String(r?.data?.name || ''))) {
      let args; try { args = JSON.parse(r.data.arguments); } catch { continue; }
      const msgs = Array.isArray(args?.messages) ? args.messages : (args?.text ? [args.text] : []);
      for (const m of msgs) replies.push(String(m || ''));
    }
  }
  flush();
}
out.end();
console.log(JSON.stringify({ sessions, pairs }));
