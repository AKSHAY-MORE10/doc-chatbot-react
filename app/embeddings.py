"""Embedding providers for document vectorization."""

import logging
from typing import List

from langchain_core.embeddings import Embeddings
from langchain_ollama import OllamaEmbeddings

from app.config import settings
from app.http_utils import json_post, normalize_base_url

try:
    from urllib import parse as urllib_parse
except ImportError:  # pragma: no cover
    import urllib.parse as urllib_parse

logger = logging.getLogger(__name__)


class GeminiEmbeddings(Embeddings):
    """Langchain-compatible wrapper around the Gemini embedContent REST API."""

    def __init__(self, api_key: str, model: str, base_url: str) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url

    def _embed_single(self, text: str) -> list[float]:
        query = urllib_parse.urlencode({"key": self._api_key.strip()})
        response = json_post(
            f"{normalize_base_url(self._base_url)}/models/"
            f"{urllib_parse.quote(self._model, safe='')}:embedContent?{query}",
            {"content": {"parts": [{"text": text}]}},
        )
        embedding = response.get("embedding") or {}
        values = embedding.get("values") or []
        if not values:
            raise RuntimeError("Gemini returned no embedding values")
        return values

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._embed_single(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed_single(text)


def get_embeddings() -> Embeddings:
    """Return the configured embedding model (Gemini or Ollama)."""
    use_gemini = settings.LLM_PROVIDER == "gemini" or settings.EMBED_PROVIDER == "gemini"

    if use_gemini:
        if not settings.LLM_API_KEY.strip():
            raise ValueError("LLM_API_KEY is required when Gemini embeddings are enabled")
        return GeminiEmbeddings(
            api_key=settings.LLM_API_KEY,
            model=settings.EMBED_MODEL,
            base_url=settings.GEMINI_API_BASE_URL,
        )

    return OllamaEmbeddings(
        model=settings.EMBED_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
    )
