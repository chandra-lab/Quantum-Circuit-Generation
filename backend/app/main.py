"""FastAPI application entrypoint."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import Settings, get_settings
from app.core.errors import AppError, error_payload
from app.services.explanation import explain_errors
from app.services.history import build_history
from app.services.llm.groq import GroqProvider
from app.utils.redact import install_redaction

logger = logging.getLogger(__name__)

LEARNER_EXPLAINED_ERRORS = frozenset({"validation_error", "measurements_required"})


# Multipart boundaries, headers, and the optional prompt field.
UPLOAD_OVERHEAD_BYTES = 64 * 1024


class RequestSizeLimitMiddleware:
    def __init__(
        self,
        app: object,
        max_bytes: int,
        path_limits: dict[str, int] | None = None,
    ) -> None:
        self.app = app
        self.max_bytes = max_bytes
        self.path_limits = path_limits or {}

    async def __call__(self, scope: dict, receive: object, send: object) -> None:
        if scope["type"] == "http" and scope.get("method") in {"POST", "PUT", "PATCH"}:
            headers = {
                key.decode("latin-1").lower(): value.decode("latin-1")
                for key, value in scope.get("headers", [])
            }
            length = headers.get("content-length")
            if length is not None:
                try:
                    size = int(length)
                except ValueError:
                    size = 0
                path = scope.get("path", "")
                limit = self.path_limits.get(path, self.max_bytes)
                if size > limit:
                    response = JSONResponse(
                        status_code=413,
                        content={
                            "error": {
                                "code": (
                                    "file_too_large"
                                    if path in self.path_limits
                                    else "payload_too_large"
                                ),
                                "message": f"Request body exceeds {limit} bytes.",
                                "details": [],
                            }
                        },
                    )
                    await response(scope, receive, send)
                    return
        await self.app(scope, receive, send)  # type: ignore[operator]


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    install_redaction(settings.groq_api_key)
    app = FastAPI(
        title="LLM-Based Quantum Circuit Generation",
        summary="Natural language to validated, simulated quantum circuits.",
        version="0.1.0",
    )
    app.state.settings = settings
    app.state.history = build_history(settings.history_enabled, settings.history_database_path)
    app.state.llm = GroqProvider(settings)

    app.add_middleware(
        RequestSizeLimitMiddleware,
        max_bytes=settings.max_request_bytes,
        path_limits={
            "/api/circuits/generate-from-file": settings.max_upload_bytes + UPLOAD_OVERHEAD_BYTES,
        },
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list or ["http://localhost:8080"],
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Accept"],
    )

    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        content = error_payload(exc)
        if exc.code in LEARNER_EXPLAINED_ERRORS:
            content["learner_explanation"] = explain_errors(exc.details, message=exc.message)
        return JSONResponse(status_code=exc.status_code, content=content)

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(
        _request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        details: list[str] = []
        for error in exc.errors():
            location = ".".join(str(part) for part in error["loc"] if part != "body")
            message = str(error["msg"])
            details.append(f"{location}: {message}" if location else message)
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "validation_error",
                    "message": "Request validation failed.",
                    "details": details,
                }
            },
        )

    app.include_router(router, prefix="/api")
    logger.info(
        "service ready llm_configured=%s model=%s",
        settings.llm_configured,
        settings.groq_model,
    )
    return app


app = create_app()
