"""Contract every language-model provider implements."""

from __future__ import annotations

from typing import Protocol


class CircuitLLM(Protocol):
    provider_name: str

    def ensure_configured(self) -> None:
        """Raise ConfigurationError when the provider cannot be called."""

    async def complete(self, messages: list[dict[str, str]], *, strict: bool) -> str:
        """Return the raw model message. Callers parse and validate it."""
