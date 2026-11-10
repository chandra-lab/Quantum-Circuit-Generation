"""Retry a provider until it returns a validated circuit spec."""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass

from app.core.config import Settings
from app.core.errors import (
    AppError,
    CircuitValidationError,
    LLMMalformedJSONError,
    LLMProviderError,
    LLMRateLimitError,
    LLMSchemaUnsupportedError,
    LLMTimeoutError,
)
from app.schemas.circuit import CircuitSpec, inspect_spec
from app.services.llm.base import CircuitLLM
from app.services.llm.prompts import correction_message, system_prompt


@dataclass
class GeneratedCircuit:
    spec: CircuitSpec
    attempts: int
    provider: str
    model: str


def parse_json_object(raw: str) -> dict:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LLMMalformedJSONError() from exc
    if not isinstance(value, dict):
        raise LLMMalformedJSONError("The language model returned JSON that is not an object.")
    return value


async def _complete(provider: CircuitLLM, messages: list[dict[str, str]], *, strict: bool) -> str:
    try:
        return await provider.complete(messages, strict=strict)
    except LLMSchemaUnsupportedError:
        if not strict:
            raise LLMProviderError(
                "The configured model does not support structured JSON output."
            ) from None
        return await provider.complete(messages, strict=False)


async def request_circuit_spec(
    provider: CircuitLLM,
    prompt: str,
    settings: Settings,
) -> GeneratedCircuit:
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_prompt(settings.max_qubits)},
        {"role": "user", "content": prompt},
    ]
    attempts = settings.llm_max_retries
    last_errors: list[str] = []
    last_payload: dict | None = None
    last_error: AppError | None = None

    for attempt in range(1, attempts + 1):
        try:
            raw = await _complete(provider, messages, strict=True)
            payload = parse_json_object(raw)
            spec, errors = inspect_spec(
                payload,
                max_qubits=settings.max_qubits,
                max_gates=settings.max_gates,
            )
            if spec is not None and not errors:
                return GeneratedCircuit(
                    spec=spec,
                    attempts=attempt,
                    provider=provider.provider_name,
                    model=settings.groq_model,
                )
            last_errors = errors
            last_payload = payload
            last_error = CircuitValidationError(errors, spec=payload)
            messages = [
                *messages,
                {"role": "assistant", "content": raw[:6000]},
                {"role": "user", "content": correction_message(errors)},
            ]
        except LLMMalformedJSONError as exc:
            last_errors = []
            last_payload = None
            last_error = exc
            messages = [
                *messages,
                {
                    "role": "user",
                    "content": "That was not a JSON object. Return only the circuit JSON object.",
                },
            ]
        except (LLMRateLimitError, LLMTimeoutError, LLMProviderError) as exc:
            last_errors = []
            last_payload = None
            last_error = exc

        if attempt < attempts:
            await asyncio.sleep(min(8.0, 0.5 * (2 ** (attempt - 1))))

    if last_error is not None:
        if isinstance(last_error, CircuitValidationError):
            raise CircuitValidationError(last_errors, spec=last_payload)
        raise last_error
    raise LLMProviderError("The language model did not return a circuit.")
