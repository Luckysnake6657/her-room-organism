# -*- coding: utf-8 -*-
"""数据边界 v0：告知、导出、删除。

原则：
- 用户的对话与记忆只存本地；出去的只有"发给模型的那一段"（简报 + 本子条目 + 当前这句）。
- API key 是**设备配置**，不算用户数据：导出不含它，删除也不动它。
- 删除要能验证：删完查不到，才算删了。

v0 不做加密（本地明文）；加密是下一版。
"""
import json
import os
import time

from . import api_client


def _read_json(path):
    if not path or not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def disclosure() -> str:
    """一段人话，给用户看。"""
    return (
        "她只把这几样存在这台电脑上：\n"
        "1. 她的身体状态和世界（一个存档文件）；\n"
        "2. 你告诉过她的事（本子，一条一条，你可以看、可以改、可以删）；\n"
        "3. 你们这次会话的往来（只在内存和存档里，不单独留存聊天记录）。\n"
        "\n"
        "每次她回话，会把这些发送给模型服务：她的状态摘要、本子上相关的几条、"
        "以及你刚说的那句。不会发：你的账号、你的其他文件、API key。\n"
        "\n"
        "想拿走：运行导出，得到一个 JSON。\n"
        "想删掉：运行删除，删掉存档和本子；删完会再查一遍，确认查不到。\n"
        "API key 不在删除范围内——那是这台设备的配置，不是你的数据。"
    )


def export(session_path: str, notebook_path: str = None, out: str = None) -> dict:
    bundle = dict(
        exported_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        session=_read_json(session_path),
        notebook=_read_json(notebook_path),
        note="不含 API key；key 属于设备配置，不随数据导出。",
    )
    if out:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(bundle, f, ensure_ascii=False, indent=2)
    return bundle


def delete(session_path: str, notebook_path: str = None) -> dict:
    removed, missing = [], []
    for p in (session_path, notebook_path):
        if not p:
            continue
        if os.path.exists(p):
            os.remove(p)
            removed.append(p)
        else:
            missing.append(p)
    # 验证：删完必须查不到
    still = [p for p in (session_path, notebook_path) if p and os.path.exists(p)]
    return dict(removed=removed, missing=missing, still_exists=still,
                ok=not still)


def api_key_local() -> bool:
    """key 是否只在本机配置里（不落仓库、不随导出）。"""
    cfg = api_client.resolve()
    return bool(cfg.get("api_key"))
