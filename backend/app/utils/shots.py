"""Shot-count checks shared by simulate endpoints."""

from __future__ import annotations

from app.core.config import Settings
from app.core.errors import AppError


def resolve_shots(requested: int | None, settings: Settings) -> int:
    shots = settings.shots if requested is None else requested
    if isinstance(shots, bool) or not isinstance(shots, int):
        raise AppError(400, "invalid_shots", "shots must be an integer.")
    if shots < 1:
        raise AppError(400, "invalid_shots", "shots must be at least 1.")
    if shots > settings.max_shots:
        raise AppError(
            400,
            "invalid_shots",
            f"shots cannot exceed MAX_SHOTS ({settings.max_shots}).",
        )
    return shots
