"""Environment-backed settings. The Groq key stays on the server."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    groq_timeout_seconds: float = 45.0
    max_qubits: int = Field(default=8, ge=1, le=16)
    max_shots: int = Field(default=10_000, ge=1, le=100_000)
    shots: int = Field(default=1000, ge=1, le=100_000)
    llm_max_retries: int = Field(default=3, ge=1, le=6)
    cors_origins: str = "http://localhost:8080,http://localhost:5173"
    max_request_bytes: int = Field(default=65_536, ge=1024, le=1_000_000)
    max_prompt_chars: int = Field(default=4000, ge=1, le=8000)
    max_gates: int = Field(default=128, ge=1, le=512)
    history_enabled: bool = True
    history_database_path: str = "data/history.db"

    @field_validator("groq_api_key", "groq_model", "cors_origins", "history_database_path")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def shots_within_cap(self) -> Settings:
        if self.shots > self.max_shots:
            raise ValueError("SHOTS cannot exceed MAX_SHOTS")
        return self

    @property
    def llm_configured(self) -> bool:
        return bool(self.groq_api_key)

    @property
    def cors_origin_list(self) -> list[str]:
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
