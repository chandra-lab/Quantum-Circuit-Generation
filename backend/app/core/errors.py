"""Structured application errors returned by the API."""

from __future__ import annotations

from typing import Any


class AppError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: list[str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or []
        self.extra = extra or {}


class ConfigurationError(AppError):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            503,
            "configuration_error",
            message
            or (
                "GROQ_API_KEY is not configured. Natural-language generation needs a "
                "Groq API key. Predefined reference circuits can still be simulated."
            ),
        )


class CircuitValidationError(AppError):
    def __init__(self, details: list[str], spec: dict[str, Any] | None = None) -> None:
        message = details[0] if details else "Circuit spec is invalid."
        extra = {"spec": spec} if spec is not None else None
        super().__init__(422, "validation_error", message, details, extra)


class LLMRateLimitError(AppError):
    def __init__(self) -> None:
        super().__init__(
            429,
            "rate_limit",
            "The language model provider is rate limiting requests. Wait a moment and try again.",
        )


class LLMMalformedJSONError(AppError):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            502,
            "llm_malformed_json",
            message
            or "The language model returned malformed JSON. Try rephrasing the prompt.",
        )


class LLMProviderError(AppError):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            502,
            "llm_error",
            message
            or (
                "The language model request failed. Check that GROQ_API_KEY is valid "
                "and that GROQ_MODEL supports JSON output."
            ),
        )


class LLMTimeoutError(AppError):
    def __init__(self) -> None:
        super().__init__(
            504,
            "llm_timeout",
            "The language model request timed out. Try again in a moment.",
        )


class LLMSchemaUnsupportedError(AppError):
    """The configured model rejected json_schema mode. Callers may retry with json_object."""

    def __init__(self) -> None:
        super().__init__(
            502,
            "llm_schema_unsupported",
            "The configured model does not support structured JSON schema output.",
        )


class FileTooLargeError(AppError):
    def __init__(self, max_mb: int) -> None:
        super().__init__(
            413,
            "file_too_large",
            f"The uploaded file exceeds {max_mb} MB.",
        )


class UnsupportedFileTypeError(AppError):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            415,
            "unsupported_media_type",
            message or "Upload a PNG, JPEG, WebP, or PDF file.",
        )


class ExtractionError(AppError):
    """Nothing usable could be read from an uploaded file."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "extraction_failed",
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(422, code, message, extra=extra)


class SimulationError(AppError):
    def __init__(self, message: str | None = None) -> None:
        super().__init__(
            500,
            "simulation_error",
            message or "The quantum simulator could not run this circuit.",
        )


def error_payload(error: AppError) -> dict[str, Any]:
    body: dict[str, Any] = {
        "error": {
            "code": error.code,
            "message": error.message,
            "details": error.details,
        }
    }
    body.update(error.extra)
    return body
