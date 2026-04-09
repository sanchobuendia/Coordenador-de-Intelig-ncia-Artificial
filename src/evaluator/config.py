"""Runtime configuration helpers."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover
    def load_dotenv() -> None:
        return None

load_dotenv()

DEFAULT_MODEL_PROVIDER = "bedrock_converse"
DEFAULT_BEDROCK_MODEL_ID = ""
DEFAULT_MODEL_TEMPERATURE = 0.2


def _get_env(*names: str, default: str | None = None) -> str | None:
    load_dotenv()
    for name in names:
        value = os.getenv(name)
        if value is not None and value.strip():
            return value.strip()
    return default


class Settings(BaseModel):
    model_provider: str = Field(default=DEFAULT_MODEL_PROVIDER)
    bedrock_model_id: str = Field(default=DEFAULT_BEDROCK_MODEL_ID)
    model_temperature: float = Field(default=DEFAULT_MODEL_TEMPERATURE)
    aws_region: str = Field(default="")
    db_path: str = Field(default="")
    log_level: str = Field(default="INFO")

    @property
    def MODEL_PROVIDER(self) -> str:
        return self.model_provider

    @property
    def BEDROCK_MODEL_ID(self) -> str:
        return self.bedrock_model_id

    @property
    def MODEL_TEMPERATURE(self) -> float:
        return self.model_temperature

    @property
    def DB_PATH(self) -> str:
        return self.db_path

    @property
    def LOG_LEVEL(self) -> str:
        return self.log_level

    @property
    def AWS_REGION(self) -> str:
        return self.aws_region


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        model_provider=_get_env("MODEL_PROVIDER", "model_provider", default=DEFAULT_MODEL_PROVIDER),
        bedrock_model_id=_get_env("BEDROCK_MODEL_ID", "bedrock_model_id", default=DEFAULT_BEDROCK_MODEL_ID),
        model_temperature=float(_get_env("MODEL_TEMPERATURE", "model_temperature", default=str(DEFAULT_MODEL_TEMPERATURE)) or DEFAULT_MODEL_TEMPERATURE),
        aws_region=_get_env("AWS_REGION", "aws_region", default=""),
        db_path=_get_env("DB_PATH", "db_path", default=""),
        log_level=(_get_env("LOG_LEVEL", "log_level", default="INFO") or "INFO").upper(),
    )


def get_chat_model():
    from langchain.chat_models import init_chat_model

    settings = get_settings()
    if not settings.bedrock_model_id.strip():
        raise ValueError("BEDROCK_MODEL_ID is not configured")

    return init_chat_model(
        settings.bedrock_model_id,
        model_provider=settings.model_provider,
        temperature=settings.model_temperature,
    )


class FallbackChatModel:
    def __init__(self, primary_model: Any, fallback_model: Any | None = None):
        self.primary_model = primary_model
        self.fallback_model = fallback_model

    def with_structured_output(self, schema):
        primary = self.primary_model.with_structured_output(schema)
        fallback = self.fallback_model.with_structured_output(schema) if self.fallback_model else None
        return FallbackChatModel(primary, fallback)

    def invoke(self, *args, **kwargs):
        try:
            return self.primary_model.invoke(*args, **kwargs)
        except Exception as exc:
            if self.fallback_model and "The provided model identifier is invalid" in str(exc):
                return self.fallback_model.invoke(*args, **kwargs)
            raise


def build_chat_model_with_fallback():
    primary_model = get_chat_model()
    return FallbackChatModel(primary_model, None)
