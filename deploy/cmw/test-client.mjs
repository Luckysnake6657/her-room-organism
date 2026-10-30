// 契约测试：身体服务的三个接口。桥接接入前先跑这个。
// 用法：node test-client.mjs [baseUrl]
import { health, form, absence } from './organism-client.mjs';

const base = process.argv[2] || 'http://127.0.0.1:3210';
const die = (code, msg) => { console.error('FAIL:', msg); process.exit(code); };

const h = await health(base);
if (!h || typeof h.t !== 'number') die(1, 'health 没有返回 t');
if (!h.state) die(1, 'health 没有 state');

const f = await form(base, 'owner', '今天怎么样');
if (!f) die(2, 'form 没有返回');
if (!(f.delay_s >= 8 && f.delay_s <= 300)) die(2, 'delay 超出 8–300');
if (!(f.words_hint >= 12 && f.words_hint <= 180)) die(2, 'words 超出 12–180');

const a = await absence(base, 'owner', 1440);
if (!a) die(3, 'absence 没有返回');
if (!a.settlement) die(3, 'absence 没有结算');
if (!a.disclosure) die(3, 'absence 没有披露');

console.log('ok', JSON.stringify({ t: h.t, delay: f.delay_s, words: f.words_hint, days: a.days }));
