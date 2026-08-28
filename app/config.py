import logging
from pathlib import Path

from dotenv import set_key, unset_key
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

# Only these keys may be written via the /settings/llm endpoint.
_ALLOWED_PERSIST_KEYS = frozenset({
    "LLM_PROVIDER",
    "LLM_MODEL",
    "EMBED_MODEL",
    "EMBED_PROVIDER",
    "OLLAMA_BASE_URL",
    "LLM_API_BASE_URL",
    "GEMINI_API_BASE_URL",
    "LLM_API_KEY",
})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore")

    LLM_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "qwen2.5:7b"
    LLM_API_KEY: str = ""
    LLM_API_BASE_URL: str = "https://api.x.ai/v1"
    EMBED_PROVIDER: str = "ollama"
    EMBED_MODEL: str = "nomic-embed-text"
    GEMINI_API_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta"
    CHROMA_PATH: str = "./chroma_data"
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150
    TOP_K: int = 4
    MAX_UPLOAD_MB: int = 20
    ADMIN_API_KEY: str = ""
    ALLOWED_ORIGINS: str = "http://127.0.0.1:8000,http://localhost:8000"
    RATE_LIMIT_RPM: int = 30


settings = Settings()


def _apply_settings(new_settings: Settings) -> Settings:
    for field_name in new_settings.model_dump().keys():
        object.__setattr__(settings, field_name, getattr(new_settings, field_name))
    return settings


def reload_settings() -> Settings:
    return _apply_settings(Settings())


def persist_settings(updates: dict[str, str | None]) -> Settings:
    """Write allowed settings to .env and reload.

    Only keys in ``_ALLOWED_PERSIST_KEYS`` are accepted; any other key is
    silently dropped to prevent an API caller from overwriting arbitrary
    environment variables (e.g. ``ADMIN_API_KEY``).
    """
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)

    for key, value in updates.items():
        if key not in _ALLOWED_PERSIST_KEYS:
            logger.warning("persist_settings: rejected disallowed key %r", key)
            continue

        if value is None or value == "":
            unset_key(str(ENV_FILE), key)
        else:
            set_key(str(ENV_FILE), key, value)

    return reload_settings()