# -*- coding: utf-8 -*-
"""本地中文向量：bge-small-zh（512 维），不走 API（DeepSeek 没有 embeddings）。

HF 直连不通时走镜像；模型只加载一次。
"""
import os

_model = None


def _get():
    global _model
    if _model is None:
        os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("BAAI/bge-small-zh-v1.5")
    return _model


def encode(texts):
    return _get().encode(list(texts), normalize_embeddings=True)


def cosine(a, b) -> float:
    return float(sum(x * y for x, y in zip(a, b)))
