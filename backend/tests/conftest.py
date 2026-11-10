"""Shared fixtures. Tests never call Groq."""

from __future__ import annotations

import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.quantum.examples import BELL_SPEC


def make_settings(tmp_path, **overrides) -> Settings:
    values = {
        "groq_api_key": "",
        "groq_model": "openai/gpt-oss-20b",
        "max_qubits": 8,
        "max_shots": 10000,
        "shots": 1000,
        "llm_max_retries": 3,
        "history_enabled": True,
        "history_database_path": str(tmp_path / "history.db"),
        "max_request_bytes": 65536,
        "max_prompt_chars": 4000,
        "cors_origins": "http://localhost:8080",
    }
    values.update(overrides)
    return Settings(**values)


@pytest.fixture
def settings(tmp_path) -> Settings:
    return make_settings(tmp_path)


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    application = create_app(settings)
    with TestClient(application) as test_client:
        yield test_client


class FakeLLM:
    provider_name = "fake"

    def __init__(self, responses: list[object]) -> None:
        self._responses = list(responses)
        self.calls: list[bool] = []

    def ensure_configured(self) -> None:
        return None

    async def complete(self, messages: list[dict[str, str]], *, strict: bool) -> str:
        self.calls.append(strict)
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return str(item)


def bell_json() -> str:
    return json.dumps(BELL_SPEC)
