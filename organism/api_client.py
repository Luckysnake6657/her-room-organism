# -*- coding: utf-8 -*-
"""API 客户端：任何 OpenAI 兼容的 /chat/completions 都能用。

Key 不进仓库。优先级：
1. 环境变量（DSH_API_KEY / DSH_BASE_URL / DSH_MODEL）
2. 本地未跟踪的 config.local.json
3. 内置默认值（DeepSeek 的公开地址）

换供应商只改 config.local.json 三行：base_url、model、api_key。
"""
import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.normpath(os.path.join(HERE, "..", "config.local.json"))

DEFAULTS = dict(
    base_url="https://api.deepseek.com/v1",
    model="deepseek-chat",
    timeout=20,
    max_tokens=200,
    temperature=0.8,
    api_key="",
)


def resolve() -> dict:
    cfg = dict(DEFAULTS)
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    for env, key in (("DSH_API_KEY", "api_key"),
                     ("DSH_BASE_URL", "base_url"),
                     ("DSH_MODEL", "model")):
        if os.environ.get(env):
            cfg[key] = os.environ[env]
    return cfg


def available() -> bool:
    return bool(resolve().get("api_key"))


def chat(system: str, user: str, max_tokens: int = None,
         temperature: float = None, model: str = None) -> str:
    cfg = resolve()
    if not cfg["api_key"]:
        raise RuntimeError("no api key")
    payload = dict(
        model=model or cfg["model"],
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}],
        max_tokens=max_tokens or cfg["max_tokens"],
        temperature=cfg["temperature"] if temperature is None else temperature,
        stream=False,
    )
    req = urllib.request.Request(
        cfg["base_url"].rstrip("/") + "/chat/completions",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + cfg["api_key"]},
    )
    with urllib.request.urlopen(req, timeout=cfg["timeout"]) as r:
        data = json.load(r)
    return data["choices"][0]["message"]["content"].strip()
