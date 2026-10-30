// 桥接模拟：按桥接将要用的方式调身体，打印它该插进提示词/发送前的东西。
// 用法：node bridge-sim.mjs [baseUrl]
import { health, form, absence } from './organism-client.mjs';

const base = process.argv[2] || 'http://127.0.0.1:3210';
const peer = 'owner';

const h = await health(base);
if (!h) { console.error('身体没起来'); process.exit(1); }
console.log('[健康]', h.state, 'D=' + h.D, 'u=' + h.u, 't=' + h.t);

const f1 = await form(base, peer, '我回来了');
console.log('[提示词该加]', f1 ? `【你现在】${f1.state}` : '(身体不可用，回退)');
console.log('[发送前该等]', f1 ? `${Math.min(f1.delay_s, 300)} 秒` : '0 秒');

const a = await absence(base, peer, 1440);
console.log('[缺席结算]', a.settlement);
console.log('[缺席披露]', a.disclosure);

const f2 = await form(base, peer, '今天怎么样');
console.log('[第二轮]', `延迟 ${f2.delay_s}s / 字数 ${f2.words_hint} / 主动 ${f2.proactive}`);

if (!(f1 && f2 && a && a.settlement && a.disclosure)) process.exit(2);
console.log('ok');
