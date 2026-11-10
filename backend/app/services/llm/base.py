"""Contract every language-model provider implements."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ImageInput:
    media_type: str
    data: bytes


class CircuitLLM(Protocol):
    provider_name: str

    def ensure_configured(self) -> None:
        """Raise ConfigurationError when the provider cannot be called."""

    async def complete(self, messages: list[dict[str, str]], *, strict: bool) -> str:
        """Return the raw model message. Callers parse and validate it."""

    async def transcribe_images(
        self,
        images: list[ImageInput],
        *,
        instructions: str | None = None,
    ) -> str:
        """Return a plain-text transcription of the question shown in the images.

        The result is treated as untrusted text. It is only ever fed back into
        circuit-spec generation, never executed.
        """
