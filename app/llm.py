"""LLM chat provider factory — Ollama, Groq (OpenAI-compatible), and Gemini."""

import logging
from typing import Callable

from langchain_ollama import OllamaLLM

from app.config import settings
from app.http_utils import json_post, normalize_base_url

try:
    from urllib import parse as urllib_parse
except ImportError:  # pragma: no cover
    import urllib.parse as urllib_parse

logger = logging.getLogger(__name__)


def _openai_compatible_chat(prompt: str, base_url: str, api_key: str, model: str) -> str:
    """Call an OpenAI-compatible chat completions endpoint (Groq, etc.)."""
    response = json_post(
        f"{normalize_base_url(base_url)}/chat/completions",
        {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant for a document chatbot."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.5,
        },
        headers={"Authorization": f"Bearer {api_key.strip()}"} if api_key.strip() else None,
    )
    choices = response.get("choices") or []
    if not choices:
        raise RuntimeError("Chat API returned no choices")
    message = choices[0].get("message") or {}
    content = message.get("content") or ""
    if not content.strip():
        raise RuntimeError("Chat API returned an empty response")
    return content


def _gemini_chat(prompt: str, api_key: str, model: str, base_url: str) -> str:
    """Call the Gemini generateContent REST API."""
    query = urllib_parse.urlencode({"key": api_key.strip()})
    response = json_post(
        f"{normalize_base_url(base_url)}/models/"
        f"{urllib_parse.quote(model, safe='')}:generateContent?{query}",
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.5},
        },
    )
    candidates = response.get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini returned no candidates")
    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    text = "".join(part.get("text", "") for part in parts)
    if not text.strip():
        raise RuntimeError("Gemini returned an empty response")
    return text


def get_chat_model() -> Callable[[str], str]:
    """Return a callable ``(prompt: str) -> str`` for the configured LLM provider."""
    if settings.LLM_PROVIDER == "groq":
        return lambda prompt: _openai_compatible_chat(
            prompt,
            settings.LLM_API_BASE_URL,
            settings.LLM_API_KEY,
            settings.LLM_MODEL,
        )

    if settings.LLM_PROVIDER == "gemini":
        return lambda prompt: _gemini_chat(
            prompt,
            settings.LLM_API_KEY,
            settings.LLM_MODEL,
            settings.GEMINI_API_BASE_URL,
        )

    llm = OllamaLLM(
        model=settings.LLM_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0.5,
    )
    return llm.invoke
