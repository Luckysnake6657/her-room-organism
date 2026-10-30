// 身体客户端：放进 qq-bridge/src/ 用。
// 只取状态与形式，不取文本；任何失败都返回 null，让桥接回到原行为。

const DEFAULT_BASE = 'http://127.0.0.1:3210';

async function post(base, path, body, timeoutMs) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), timeoutMs);
  try {
    const r = await fetch(base.replace(/\/$/, '') + path, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
      signal: ctl.signal,
    });
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

export async function form(base = DEFAULT_BASE, peer, text, timeoutMs = 800) {
  return post(base, '/form', { peer, text }, timeoutMs);
}

export async function absence(base = DEFAULT_BASE, peer, minutes, timeoutMs = 1500) {
  return post(base, '/absence', { peer, minutes }, timeoutMs);
}

export async function health(base = DEFAULT_BASE, timeoutMs = 500) {
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), timeoutMs);
  try {
    const r = await fetch(base.replace(/\/$/, '') + '/health', { signal: ctl.signal });
    return r.ok ? await r.json() : null;
  } catch {
    return null;
  } finally {
    clearTimeout(timer);
  }
}
