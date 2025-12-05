"""
Embedding utilities for Archive Agents.

Currently uses OpenAI embedding models; keep provider configurable via env.
"""

import os
from typing import Iterable, List

from openai import AsyncOpenAI


DEFAULT_EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-large")


def _get_client() -> AsyncOpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    return AsyncOpenAI(api_key=api_key)


async def embed_text(text: str, model: str | None = None) -> List[float]:
    """Embed a single text string."""
    embeddings = await embed_texts([text], model=model)
    return embeddings[0]


async def embed_texts(texts: Iterable[str], model: str | None = None) -> List[List[float]]:
    """Embed multiple texts and return vectors."""
    client = _get_client()
    model_name = model or DEFAULT_EMBED_MODEL
    response = await client.embeddings.create(model=model_name, input=list(texts))
    # Response ordering matches input ordering
    return [item.embedding for item in response.data]

