import re
from typing import List

from pydantic import BaseModel, Field, field_validator


_COLLECTION_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")


class ChatTurn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=10_000)


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=10_000)
    collection: str = Field(default="default", min_length=1, max_length=64)
    history: List[ChatTurn] = Field(default_factory=list, max_length=50)

    @field_validator("collection")
    @classmethod
    def validate_collection_name(cls, value: str) -> str:
        value = value.strip()
        if not _COLLECTION_RE.match(value):
            raise ValueError(
                "Collection name must start with a letter or digit and contain only "
                "letters, digits, hyphens, and underscores"
            )
        return value


class LLMSettingsRequest(BaseModel):
    provider: str = Field(pattern="^(ollama|groq|gemini)$")
    model: str = Field(min_length=1, max_length=200)
    embed_model: str = Field(min_length=1, max_length=200)
    api_key: str = Field(default="", max_length=10_000)
    ollama_base_url: str = Field(default="http://localhost:11434", max_length=500)
    api_base_url: str = Field(default="https://api.x.ai/v1", max_length=500)
    gemini_base_url: str = Field(
        default="https://generativelanguage.googleapis.com/v1beta", max_length=500
    )

    @field_validator("ollama_base_url", "api_base_url", "gemini_base_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        value = value.strip()
        if value and not value.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return value


class LLMSettingsResponse(BaseModel):
    provider: str
    model: str
    embed_model: str
    ollama_base_url: str
    api_base_url: str
    gemini_base_url: str
    api_key_saved: bool


class IngestResponse(BaseModel):
    collection: str
    chunks_added: int
    filename: str


class ChatResponse(BaseModel):
    answer: str
    sources: List[str] = Field(default_factory=list)
    web_sources: List[str] = Field(default_factory=list)