"""Application workflows for validate, simulate, and generate."""

from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.core.errors import CircuitValidationError
from app.quantum.simulator import simulate_spec
from app.quantum.visualizer import circuit_to_svg
from app.schemas.circuit import CircuitSpec, inspect_spec
from app.services.explanation import explain_result
from app.services.generation import GeneratedCircuit, request_circuit_spec
from app.services.history import RunHistoryRepository, RunRecord, safe_record
from app.services.llm.base import CircuitLLM
from app.utils.shots import resolve_shots


def _record(
    history: RunHistoryRepository,
    *,
    kind: str,
    source: str,
    prompt: str | None,
    spec: CircuitSpec | None,
    valid: bool,
) -> None:
    safe_record(
        history,
        RunRecord(
            kind=kind,
            source=source,
            prompt=prompt,
            circuit_name=spec.circuit_name if spec else None,
            num_qubits=spec.num_qubits if spec else None,
            valid=valid,
        ),
    )


def validate_payload(payload: Any, settings: Settings) -> dict[str, Any]:
    spec, errors = inspect_spec(
        payload,
        max_qubits=settings.max_qubits,
        max_gates=settings.max_gates,
    )
    return {
        "valid": spec is not None and not errors,
        "errors": errors,
        "spec": spec.public_dict() if spec is not None else None,
    }


def simulation_body(
    spec: CircuitSpec,
    *,
    shots: int,
    seed: int | None = None,
) -> dict[str, Any]:
    output, circuit = simulate_spec(spec, shots=shots, seed=seed)
    svg = circuit_to_svg(circuit)
    return {
        "spec": spec.public_dict(),
        "validation": {"valid": True, "errors": []},
        "shots": output.shots,
        "counts": output.counts,
        "probabilities": output.probabilities,
        "metadata": {
            "num_qubits": spec.num_qubits,
            "num_clbits": spec.num_clbits,
            "gates_applied": output.gates_applied,
            "simulator": "qiskit-aer",
            "shots": output.shots,
        },
        "visualization": {"format": "image/svg+xml", "svg": svg},
        "learner_explanation": explain_result(spec, shots=output.shots, counts=output.counts),
    }


def run_simulation(
    payload: Any,
    *,
    shots: int | None,
    settings: Settings,
    history: RunHistoryRepository,
    source: str,
    seed: int | None = None,
) -> dict[str, Any]:
    resolved = resolve_shots(shots, settings)
    spec, errors = inspect_spec(
        payload,
        max_qubits=settings.max_qubits,
        max_gates=settings.max_gates,
    )
    if spec is None or errors:
        _record(history, kind="simulate", source=source, prompt=None, spec=None, valid=False)
        raise CircuitValidationError(errors)
    try:
        body = simulation_body(spec, shots=resolved, seed=seed)
    except Exception:
        _record(history, kind="simulate", source=source, prompt=None, spec=spec, valid=False)
        raise
    _record(history, kind="simulate", source=source, prompt=None, spec=spec, valid=True)
    return body


async def run_generation(
    *,
    prompt: str,
    provider: CircuitLLM,
    settings: Settings,
    history: RunHistoryRepository,
) -> dict[str, Any]:
    provider.ensure_configured()
    try:
        generated = await request_circuit_spec(provider, prompt, settings)
    except CircuitValidationError as exc:
        _record(history, kind="generate", source="llm", prompt=prompt, spec=None, valid=False)
        raise exc
    except Exception:
        _record(history, kind="generate", source="llm", prompt=prompt, spec=None, valid=False)
        raise
    _record(history, kind="generate", source="llm", prompt=prompt, spec=generated.spec, valid=True)
    return _generation_payload(prompt, generated)


async def run_generation_and_simulation(
    *,
    prompt: str,
    shots: int | None,
    provider: CircuitLLM,
    settings: Settings,
    history: RunHistoryRepository,
) -> dict[str, Any]:
    provider.ensure_configured()
    resolved = resolve_shots(shots, settings)
    try:
        generated = await request_circuit_spec(provider, prompt, settings)
        simulated = simulation_body(generated.spec, shots=resolved)
    except CircuitValidationError:
        _record(
            history,
            kind="generate_and_simulate",
            source="llm",
            prompt=prompt,
            spec=None,
            valid=False,
        )
        raise
    except Exception:
        _record(
            history,
            kind="generate_and_simulate",
            source="llm",
            prompt=prompt,
            spec=None,
            valid=False,
        )
        raise
    _record(
        history,
        kind="generate_and_simulate",
        source="llm",
        prompt=prompt,
        spec=generated.spec,
        valid=True,
    )
    return {
        "prompt": prompt,
        "source": "llm",
        **simulated,
        "metadata": {
            **simulated["metadata"],
            "provider": generated.provider,
            "model": generated.model,
            "attempts": generated.attempts,
        },
    }


def _generation_payload(prompt: str, generated: GeneratedCircuit) -> dict[str, Any]:
    spec = generated.spec
    return {
        "prompt": prompt,
        "source": "llm",
        "spec": spec.public_dict(),
        "validation": {"valid": True, "errors": []},
        "metadata": {
            "provider": generated.provider,
            "model": generated.model,
            "attempts": generated.attempts,
            "num_qubits": spec.num_qubits,
            "num_clbits": spec.num_clbits,
            "gates_applied": [gate.gate for gate in spec.gates],
        },
    }
