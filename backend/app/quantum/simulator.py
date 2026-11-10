"""Qiskit Aer sampling. PyTorch is not used here."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from qiskit_aer import AerSimulator

from app.core.errors import AppError, SimulationError
from app.quantum.builder import build_circuit
from app.schemas.circuit import CircuitSpec

logger = logging.getLogger(__name__)


@dataclass
class SimulationOutput:
    shots: int
    counts: dict[str, int]
    probabilities: dict[str, float]
    gates_applied: list[str]


def simulator_status() -> dict[str, object]:
    try:
        import qiskit_aer

        AerSimulator()
    except Exception:
        logger.warning("qiskit aer is unavailable", exc_info=True)
        return {"available": False, "name": "qiskit-aer"}
    return {"available": True, "name": "qiskit-aer", "version": qiskit_aer.__version__}


def simulate_spec(
    spec: CircuitSpec,
    *,
    shots: int,
    seed: int | None = None,
) -> tuple[SimulationOutput, object]:
    if not spec.measurements:
        raise AppError(
            400,
            "measurements_required",
            "Simulation requires at least one measurement.",
        )
    circuit = build_circuit(spec)
    try:
        backend = AerSimulator() if seed is None else AerSimulator(seed_simulator=seed)
        result = backend.run(circuit, shots=shots).result()
        if getattr(result, "success", True) is False:
            raise SimulationError()
        raw_counts = result.get_counts()
    except AppError:
        raise
    except Exception as exc:
        logger.warning("aer simulation failed: %s", type(exc).__name__)
        raise SimulationError() from exc

    if not isinstance(raw_counts, dict):
        raise SimulationError("The simulator returned an unexpected counts payload.")

    counts = {
        str(bitstring).replace(" ", ""): int(count)
        for bitstring, count in raw_counts.items()
    }
    counts = dict(sorted(counts.items()))
    probabilities = {bitstring: round(count / shots, 6) for bitstring, count in counts.items()}
    output = SimulationOutput(
        shots=shots,
        counts=counts,
        probabilities=probabilities,
        gates_applied=[gate.gate for gate in spec.gates],
    )
    return output, circuit
