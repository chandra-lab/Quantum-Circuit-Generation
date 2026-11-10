"""REST routes for health, validation, generation, and simulation."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from app.core.errors import AppError
from app.quantum.examples import example_catalog
from app.quantum.simulator import simulator_status
from app.services.workflow import (
    run_generation,
    run_generation_and_simulation,
    run_simulation,
    validate_payload,
)

logger = logging.getLogger(__name__)
router = APIRouter()


class GenerateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1, max_length=8000)


class GenerateAndSimulateRequest(GenerateRequest):
    shots: int | None = None


class SimulateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spec: dict[str, Any]
    shots: int | None = None


def _checked_prompt(prompt: str, max_chars: int) -> str:
    text = prompt.strip()
    if not text:
        raise AppError(400, "invalid_prompt", "Prompt must not be empty.")
    if len(text) > max_chars:
        raise AppError(
            400,
            "invalid_prompt",
            f"Prompt exceeds {max_chars} characters.",
        )
    return text


def torch_status() -> dict[str, object]:
    try:
        import torch
    except Exception:
        return {"available": False, "version": None}
    version = getattr(torch, "__version__", None)
    return {"available": True, "version": version if isinstance(version, str) else None}


@router.get("/health")
def health(request: Request) -> dict[str, object]:
    settings = request.app.state.settings
    simulator = simulator_status()
    pytorch = torch_status()
    api_ok = True
    return {
        "status": "ok" if api_ok else "degraded",
        "service": {"name": "llm-quantum-circuit-generation", "status": "ok"},
        "api": {"status": "ok"},
        "quantum_simulator": simulator,
        "pytorch": pytorch,
        "llm": {
            "provider": "groq",
            "configured": settings.llm_configured,
            "model": settings.groq_model,
        },
    }


@router.get("/circuits/examples")
def examples() -> dict[str, object]:
    return {"examples": example_catalog()}


@router.post("/circuits/validate")
def validate(payload: dict[str, Any], request: Request) -> dict[str, Any]:
    spec_payload = payload["spec"] if isinstance(payload.get("spec"), dict) else payload
    return validate_payload(spec_payload, request.app.state.settings)


@router.post("/circuits/simulate")
def simulate(body: SimulateRequest, request: Request) -> dict[str, Any]:
    return run_simulation(
        body.spec,
        shots=body.shots,
        settings=request.app.state.settings,
        history=request.app.state.history,
        source="user",
    )


@router.post("/circuits/generate")
async def generate(body: GenerateRequest, request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    prompt = _checked_prompt(body.prompt, settings.max_prompt_chars)
    return await run_generation(
        prompt=prompt,
        provider=request.app.state.llm,
        settings=settings,
        history=request.app.state.history,
    )


@router.post("/circuits/generate-and-simulate")
async def generate_and_simulate(
    body: GenerateAndSimulateRequest,
    request: Request,
) -> dict[str, Any]:
    settings = request.app.state.settings
    prompt = _checked_prompt(body.prompt, settings.max_prompt_chars)
    return await run_generation_and_simulation(
        prompt=prompt,
        shots=body.shots,
        provider=request.app.state.llm,
        settings=settings,
        history=request.app.state.history,
    )
