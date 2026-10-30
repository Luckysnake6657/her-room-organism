// 切训练/留出：把盲评用的那 20 轮上下文从训练集里剔掉。
import fs from 'node:fs';

const DS = 'evidence/p3/cmw_dataset';
const STATE = process.env.QQ_STATE || 'state/social-v2.json';

const s = JSON.parse(fs.readFileSync(STATE, 'utf8'));
const msgs = (s.conversations['private:owner'].recentMessages || [])
  .map((m) => ({ self: !!m.isSelf, text: String(m.text || '').trim(), t: Number(m.time) || 0 }))
  .filter((m) => m.text)
  .sort((a, b) => a.t - b.t);

// 与 shadow.pairs 同款：管理员一条 + 她随后 30 秒内的气泡
const pairs = [];
for (let i = 0; i < msgs.length; i++) {
  if (msgs[i].self) continue;
  const owner = msgs[i];
  const reply = [];
  let j = i + 1;
  let last = owner.t;
  while (j < msgs.length && msgs[j].self && msgs[j].t - last <= 30000) {
    reply.push(msgs[j].text);
    last = msgs[j].t;
    j++;
  }
  if (reply.length) pairs.push({ owner: owner.text, hers: reply.join('') });
}
const hold = pairs.slice(-20).map((p) => p.owner.replace(/\s+/g, ''));
console.log('holdout owners', hold.length);

const rows = fs.readFileSync(DS + '\\\\pairs.jsonl', 'utf8').split(/\r?\n/).filter(Boolean)
  .map((l) => JSON.parse(l));
const train = [], val = [];
for (const r of rows) {
  const ctx = r.context.replace(/\s+/g, '');
  const leaked = hold.some((h) => h.length >= 4 && ctx.includes(h));
  (leaked ? val : train).push(r);
}
fs.writeFileSync(DS + '\\\\train.jsonl', train.map((r) => JSON.stringify(r)).join('\n') + '\n', 'utf8');
fs.writeFileSync(DS + '\\\\val.jsonl', val.map((r) => JSON.stringify(r)).join('\n') + '\n', 'utf8');
console.log(JSON.stringify({ train: train.length, val: val.length }));
