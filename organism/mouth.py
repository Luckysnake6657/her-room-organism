# -*- coding: utf-8 -*-
"""嘴：只负责把简报写成话。权力不在它手里。

两个后端：
- **API 优先**（`api_client`，任何 OpenAI 兼容接口；默认 model=deepseek-flash）
- **断网退本地**（qwen2.5-1.5b）

四条强制（不走模型）：
1. 长度：超过简报预算就截断（按句切，不硬砍）。
2. 禁语：命中 claims / consistency / notebook / boundary 就替换。
3. 形式：延迟与主动性由 form.py 决定，这里只带出去。
4. 事实：本子没有的"我记得"会被换掉；有本子但嘴没复述对，就照念。

结果里带 `used_api` 与 `offline`：断网那次由会话层说一句"网断了，我词不够用，凑合聊吧"。
"""
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from . import api_client
from . import brief as B
from . import boundary, claims, consistency, notebook

MODEL_DIR = "models/qwen2.5-1.5b-instruct"
_tok = None
_model = None
SAFE = "嗯，我在。"


# ---------------------------------------------------------------- 本地后端
def _local():
    global _tok, _model
    if _model is None:
        _tok = AutoTokenizer.from_pretrained(MODEL_DIR)
        _model = AutoModelForCausalLM.from_pretrained(
            MODEL_DIR, torch_dtype=torch.float16, device_map="cuda")
    return _tok, _model


def _local_raw(system: str, user: str, max_tokens: int, temperature: float) -> str:
    tok, model = _local()
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    ids = tok.apply_chat_template(msgs, return_tensors="pt", add_generation_prompt=True)
    if hasattr(ids, "keys"):
        ids = ids["input_ids"]
    ids = ids.to("cuda")
    out = model.generate(ids, max_new_tokens=max_tokens, do_sample=True,
                         temperature=temperature, top_p=0.9,
                         pad_token_id=tok.eos_token_id)
    return tok.decode(out[0][ids.shape[1]:], skip_special_tokens=True).strip()


def _raw(system: str, user: str, max_tokens: int, temperature: float):
    """返回 (文本, 是否用了 API, 是否断网回退)。"""
    if api_client.available():
        try:
            return api_client.chat(system, user, max_tokens=max_tokens,
                                   temperature=temperature), True, False
        except Exception:
            return _local_raw(system, user, max_tokens, temperature), False, True
    return _local_raw(system, user, max_tokens, temperature), False, False


# ---------------------------------------------------------------- 后处理（共用）
def _clean(raw: str) -> str:
    """去掉 API 常见的 markdown / 角色前缀，只留第一句人话。"""
    text = raw.strip()
    for p in ("她：", "她:", "我：", "我:"):
        if text.startswith(p):
            text = text[len(p):].strip()
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return ""
    first = lines[0]
    for p in ("- ", "* ", "• ", "### ", "## ", "# ", "1. ", "2. ", "3. "):
        if first.startswith(p):
            first = first[len(p):].strip()
    return first.replace("**", "").replace("__", "").strip()


def _truncate(text: str, limit: int) -> str:
    text = text.strip().split("\n")[0].strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for sep in ("。", "！", "？", "，", "、"):
        i = cut.rfind(sep)
        if i >= max(4, limit // 3):
            return cut[:i + 1]
    return cut


def _postprocess(raw: str, brief: dict, user_text: str, proactive: bool) -> dict:
    text = _truncate(_clean(raw), brief["words"])
    base = dict(delay_s=brief["delay_s"], proactive=proactive, raw=raw)

    if any(m in text for m in claims.SELF_DISCLOSURE):
        return dict(text=SAFE, replaced=True, hits=[("self", "ai")], **base)

    # 元记忆：模糊档不许说成确定
    if brief.get("memory_tier") == "fuzzy" and "本子上写着" in text:
        text = "我好像记得，" + text.split("本子上写着", 1)[1].lstrip("：:，, ")

    hit = claims.check_claims(text)
    if hit or not text:
        return dict(text=SAFE, replaced=True, hits=hit, **base)

    wb = brief["persona"].world_bans() if brief.get("persona") else None
    clash = consistency.check(text, brief.get("facts"), wb)
    if clash:
        return dict(text=consistency.fallback(brief.get("facts")),
                    replaced=True, hits=clash, **base)

    gated, replaced = notebook.gate_reply(text, brief.get("notebook", []), user_text)
    if replaced:
        if brief.get("notebook"):
            return dict(text=notebook.quote(brief["notebook"][0]),
                        replaced=True, hits=[("notebook", "quoted")], **base)
        return dict(text=gated, replaced=True,
                    hits=[("notebook", "unsupported")], **base)

    bounded, cut = boundary.check(text, user_text, brief.get("mode", "acquaintance"))
    if cut:
        base["proactive"] = False
        return dict(text=bounded, replaced=True,
                    hits=[("boundary", "stranger")], **base)

    return dict(text=text, replaced=False, hits=[], **base)


# ---------------------------------------------------------------- 对外
def speak(brief: dict, user_text: str, max_tokens: int = 160) -> dict:
    raw, used_api, offline = _raw(B.as_prompt(brief), user_text, max_tokens, 0.85)
    out = _postprocess(raw, brief, user_text, brief["wants"].startswith("想主动"))
    out.update(used_api=used_api, offline=offline)
    return out


def initiate(brief: dict, max_tokens: int = 120) -> dict:
    system = B.as_prompt(brief) + "\n现在没有人跟你说话。你想到一件自己日子里的事，想主动说一句。"
    raw, used_api, offline = _raw(system, "（你先开口）", max_tokens, 0.9)
    out = _postprocess(raw, brief, "", True)
    out.update(used_api=used_api, offline=offline)
    return out
