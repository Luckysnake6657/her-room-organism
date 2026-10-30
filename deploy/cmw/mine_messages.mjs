// 从会话的工具结果里挖出所有抓取过的 QQ 消息（含 owner 私聊）。
// 输出 messages.jsonl：{key, seq, isSelf, isOwner, text, sender}
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';

const ROOTS = [(process.env.QQ_DSH_SESSIONS || 'sessions'), (process.env.DSH_SESSIONS || '.dsh/sessions')];
const OUT = 'D:\\deepseekharness\\lab\\dc\\evidence\\p3\\cmw_messages';

function walk(dir, acc = []) {
  let ents; try { ents = fs.readdirSync(dir, { withFileTypes: true }); } catch { return acc; }
  for (const e of ents) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) walk(p, acc);
    else if (p.endsWith('.zstd') && /qq-bridge-state-agents/.test(p)) acc.push(p);
  }
  return acc;
}

const files = ROOTS.flatMap((r) => walk(r));
fs.mkdirSync(OUT, { recursive: true });
const out = fs.createWriteStream(path.join(OUT, 'messages.jsonl'), { encoding: 'utf8' });
const seen = new Set();
let results = 0, msgs = 0;

for (const f of files) {
  let text;
  try { text = zlib.zstdDecompressSync(fs.readFileSync(f)).toString('utf8'); } catch { continue; }
  for (const l of text.split(/\r?\n/)) {
    if (!l) continue;
    let r; try { r = JSON.parse(l); } catch { continue; }
    if (r.type !== 'tool/result') continue;
    const content = r?.data?.message?.content;
    const raw = Array.isArray(content) ? content.map((c) => c.text || '').join('') : '';
    if (!raw || !raw.includes('"messages"')) continue;
    let obj;
    try { obj = JSON.parse(raw); } catch { continue; }
    if (!obj || !Array.isArray(obj.messages)) continue;
    results++;
    const key = String(obj.key || '');
    for (const m of obj.messages) {
      const seq = m.seq;
      if (seq === undefined || seq === null) continue;
      const id = key + ':' + seq;
      if (seen.has(id)) continue;
      seen.add(id);
      const t = String(m.plain || m.text || '').trim();
      if (!t) continue;
      out.write(JSON.stringify({ key, seq, isSelf: !!m.isSelf, isOwner: !!m.isOwner,
        sender: m.sender || '', text: t }) + '\n');
      msgs++;
    }
  }
}
out.end();
console.log(JSON.stringify({ files: files.length, results, msgs }));
