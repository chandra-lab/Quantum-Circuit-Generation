"""Application workflows for validate, simulate, and generate."""

from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.core.errors import AppError, CircuitValidationError, ExtractionError
from app.quantum.simulator import simulate_spec
from app.quantum.visualizer import circuit_to_svg
from app.schemas.circuit import CircuitSpec, inspect_spec
from app.services.explanation import explain_result
from app.services.generation import GeneratedCircuit, request_circuit_spec
from app.services.extraction import (
    Upload,
    cap_text,
    extract_pdf_text,
    has_meaningful_text,
    normalize_text,
    render_pdf_pages,
)
from app.services.history import RunHistoryRepository, RunRecord, safe_record
from app.services.llm.base import CircuitLLM, ImageInput
from app.services.llm.prompts import NO_QUANTUM_CONTENT, file_question_prompt
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


async def run_file_generation_and_simulation(
    *,
    upload: Upload,
    instructions: str | None,
    shots: int | None,
    provider: CircuitLLM,
    settings: Settings,
    history: RunHistoryRepository,
) -> dict[str, Any]:
    resolve_shots(shots, settings)
    extraction = await extract_question(
        upload,
        instructions=instructions,
        provider=provider,
        settings=settings,
    )
    try:
        body = await run_generation_and_simulation(
            prompt=file_question_prompt(extraction["text"], instructions),
            shots=shots,
            provider=provider,
            settings=settings,
            history=history,
        )
    except AppError as exc:
        exc.extra = {**exc.extra, "extraction": extraction}
        raise
    return {
        **body,
        "prompt": instructions or f"Uploaded file: {upload.filename}",
        "extraction": extraction,
    }


async def extract_question(
    upload: Upload,
    *,
    instructions: str | None,
    provider: CircuitLLM,
    settings: Settings,
) -> dict[str, Any]:
    """Return the question text read from an upload, with where it came from."""
    pages_read: int | None = None
    total_pages: int | None = None
    if upload.is_pdf:
        pdf = extract_pdf_text(upload.data, max_pages=settings.max_pdf_pages)
        pages_read, total_pages = pdf.pages_read, pdf.total_pages
        if has_meaningful_text(pdf.text):
            method = "pdf_text"
            raw = pdf.text
        else:
            method = "pdf_vision"
            provider.ensure_configured()
            images = render_pdf_pages(
                upload.data,
                max_pages=min(settings.pdf_vision_pages, settings.max_pdf_pages),
            )
            pages_read = len(images)
            raw = await provider.transcribe_images(images, instructions=instructions)
    else:
        method = "image_vision"
        provider.ensure_configured()
        raw = await provider.transcribe_images(
            [ImageInput(media_type=upload.media_type, data=upload.data)],
            instructions=instructions,
        )

    text = normalize_text(raw)
    if method != "pdf_text" and text.strip().strip(".").upper() == NO_QUANTUM_CONTENT:
        text = ""
    text, truncated = cap_text(text, settings.max_extracted_chars)
    extraction = {
        "filename": upload.filename,
        "media_type": upload.media_type,
        "method": method,
        "text": text,
        "truncated": truncated,
        "pages_read": pages_read,
        "total_pages": total_pages,
    }
    if not text:
        raise ExtractionError(
            "No quantum question could be read from the uploaded file.",
            code="extraction_empty",
            extra={"extraction": extraction},
        )
    return extraction
