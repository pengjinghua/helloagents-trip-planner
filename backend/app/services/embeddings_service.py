"""Embeddings service using OpenAI-compatible /embeddings endpoint.

This project already uses OpenAI-compatible chat completions via HelloAgents.
For RAG we keep dependencies minimal and call the provider's embeddings endpoint
using the same base URL and API key.

If embeddings are not available, callers should fall back to lexical retrieval.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

import httpx

from .llm_service import _normalize_openai_compatible_base_url
from ..config import get_settings


@dataclass(frozen=True)
class EmbeddingConfig:
    base_url: str
    api_key: str
    model: str
    timeout_s: float = 30.0


def _get_embedding_config() -> EmbeddingConfig:
    settings = get_settings()

    base_url = (os.getenv("LLM_BASE_URL") or settings.openai_base_url or "").strip()
    base_url = _normalize_openai_compatible_base_url(base_url)

    api_key = (os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or "").strip()

    # Allow separate embedding model; default to a common OpenAI-compatible name.
    model = (os.getenv("LLM_EMBEDDING_MODEL_ID") or os.getenv("LLM_MODEL_ID") or "").strip()

    # Heuristic: if a chat model is supplied, prefer an embedding model name.
    if model.lower().startswith(("gpt-", "qwen", "deepseek", "claude")):
        model = os.getenv("LLM_EMBEDDING_MODEL_ID") or "text-embedding-3-small"

    if not base_url:
        raise ValueError("LLM_BASE_URL 未配置，无法调用 embeddings")
    if not api_key:
        raise ValueError("LLM_API_KEY/OPENAI_API_KEY 未配置，无法调用 embeddings")

    return EmbeddingConfig(base_url=base_url.rstrip("/"), api_key=api_key, model=model)


def _embeddings_url(base_url: str) -> str:
    # base_url is expected to already include /v1
    return base_url.rstrip("/") + "/embeddings"


async def embed_texts(texts: List[str], config: Optional[EmbeddingConfig] = None) -> List[List[float]]:
    """Embed a batch of texts.

    Raises on network/provider errors.
    """

    cfg = config or _get_embedding_config()

    payload = {
        "model": cfg.model,
        "input": texts,
    }

    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=cfg.timeout_s) as client:
        resp = await client.post(_embeddings_url(cfg.base_url), json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    # OpenAI-compatible format: { data: [{embedding: [...]}, ...] }
    items = data.get("data") or []
    embeddings: List[List[float]] = []
    for item in items:
        emb = item.get("embedding")
        if not isinstance(emb, list):
            raise ValueError("embeddings 响应格式异常")
        embeddings.append([float(x) for x in emb])

    if len(embeddings) != len(texts):
        raise ValueError("embeddings 数量与输入不一致")

    return embeddings
