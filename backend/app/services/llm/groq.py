"""Groq chat completions with structured JSON. The API key is never logged."""

from __future__ import annotations

import logging

import httpx

from app.core.config import Settings
from app.core.errors import (
    ConfigurationError,
    LLMMalformedJSONError,
    LLMProviderError,
    LLMRateLimitError,
    LLMSchemaUnsupportedError,
    LLMTimeoutError,
)
from app.services.llm.schema import response_format
from app.utils.redact import redact

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqProvider:
    provider_name = "groq"

    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None) -> None:
        self._settings = settings
        self._transport = transport

    def ensure_configured(self) -> None:
        if not self._settings.llm_configured:
            raise ConfigurationError()

    async def complete(self, messages: list[dict[str, str]], *, strict: bool) -> str:
        self.ensure_configured()
        payload = {
            "model": self._settings.groq_model,
            "temperature": 0.1,
            "messages": messages,
            "response_format": response_format(strict=strict),
        }
        headers = {
            "Authorization": f"Bearer {self._settings.groq_api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(
                timeout=self._settings.groq_timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.post(GROQ_URL, headers=headers, json=payload)
        except httpx.TimeoutException as exc:
            raise LLMTimeoutError() from exc
        except httpx.HTTPError as exc:
            logger.warning("groq connection failed: %s", type(exc).__name__)
            raise LLMProviderError("Could not reach the language model provider.") from exc

        body = response.text[:2000]
        if response.status_code == 429:
            raise LLMRateLimitError()
        if response.status_code == 400 and strict and _schema_rejected(body):
            raise LLMSchemaUnsupportedError()
        if response.status_code >= 400:
            logger.warning(
                "groq request failed status=%s body=%s",
                response.status_code,
                redact(body, self._settings.groq_api_key),
            )
            raise LLMProviderError()

        try:
            data = response.json()
            content = _message_text(data["choices"][0]["message"]["content"])
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMProviderError("The language model returned an unexpected response.") from exc
        if not content.strip():
            raise LLMMalformedJSONError("The language model returned an empty response.")
        return content


def _schema_rejected(body: str) -> bool:
    lowered = body.lower()
    return "json_schema" in lowered or "response_format" in lowered or "structured" in lowered


def _message_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "".join(parts)
    raise TypeError("model content is not text")
