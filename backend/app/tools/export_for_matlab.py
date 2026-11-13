"""Export reference circuits and their Qiskit results as JSON for the MATLAB validation module.

Usage (from ``backend/``, or inside the backend container)::

    python -m app.tools.export_for_matlab --output-dir ../matlab/data/qiskit_results

Each circuit file holds the validated spec, its gate list, the exact statevector
probabilities (measurements removed), and seeded Aer counts. Bitstrings use Qiskit
order: the rightmost character is qubit 0 (or clbit 0 for sampled counts).
The output has no timestamps, so a rerun with the same versions, shots, and seed
produces identical files.
"""

from __future__ import annotations

import argparse
import json
import math
import platform
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import qiskit
import qiskit_aer
from qiskit.quantum_info import Statevector

from app.quantum.builder import build_circuit
from app.quantum.examples import BELL_SPEC, BIT_FLIP_SPEC, GHZ_SPEC, SUPERPOSITION_SPEC
from app.quantum.simulator import simulate_spec
from app.schemas.circuit import CircuitSpec, normalize_spec

SCHEMA_VERSION = 1
DEFAULT_SHOTS = 4096
DEFAULT_SEED = 1234
MANIFEST_NAME = "manifest.json"
COMMAND = "python -m app.tools.export_for_matlab"

# Bell, GHZ, and the one-qubit circuits read the same under either bit order, so a
# reversed mapping would still pass on them. These two validation-only specs are
# asymmetric and cover every supported gate, so ordering and gate-mapping bugs show up.
BIT_ORDER_PROBE_SPEC: dict[str, Any] = {
    "circuit_name": "Bit Order Probe",
    "num_qubits": 3,
    "num_clbits": 3,
    "gates": [
        {"gate": "x", "qubits": [0]},
        {"gate": "ry", "qubits": [1], "parameter": math.pi / 3},
        {"gate": "cx", "qubits": [1, 2]},
    ],
    "measurements": [
        {"qubit": 0, "clbit": 0},
        {"qubit": 1, "clbit": 1},
        {"qubit": 2, "clbit": 2},
    ],
    "description": (
        "Validation-only circuit. Qubit 0 is always 1 and qubits 1 and 2 are 1 with "
        "probability 0.25, so Qiskit reports 001 and 111 and a reversed mapping does not match."
    ),
}

GATE_COVERAGE_SPEC: dict[str, Any] = {
    "circuit_name": "Gate Coverage",
    "num_qubits": 3,
    "num_clbits": 3,
    "gates": [
        {"gate": "i", "qubits": [0]},
        {"gate": "h", "qubits": [0]},
        {"gate": "t", "qubits": [0]},
        {"gate": "h", "qubits": [0]},
        {"gate": "ry", "qubits": [1], "parameter": 0.7},
        {"gate": "s", "qubits": [1]},
        {"gate": "rx", "qubits": [1], "parameter": 1.1},
        {"gate": "x", "qubits": [2]},
        {"gate": "y", "qubits": [2]},
        {"gate": "h", "qubits": [2]},
        {"gate": "z", "qubits": [2]},
        {"gate": "cx", "qubits": [0, 1]},
        {"gate": "rz", "qubits": [2], "parameter": 0.4},
        {"gate": "cz", "qubits": [1, 2]},
        {"gate": "h", "qubits": [2]},
        {"gate": "swap", "qubits": [0, 2]},
        {"gate": "h", "qubits": [1]},
    ],
    "measurements": [
        {"qubit": 0, "clbit": 0},
        {"qubit": 1, "clbit": 1},
        {"qubit": 2, "clbit": 2},
    ],
    "description": (
        "Validation-only circuit that applies all 13 supported gates with interference, "
        "so a wrong gate, angle, control, or phase changes the probabilities."
    ),
}

# (id, source, raw spec). "reference" specs come from app/quantum/examples.py.
CIRCUITS: tuple[tuple[str, str, dict[str, Any]], ...] = (
    ("bell", "reference", BELL_SPEC),
    ("superposition", "reference", SUPERPOSITION_SPEC),
    ("ghz", "reference", GHZ_SPEC),
    ("bit_flip", "reference", BIT_FLIP_SPEC),
    ("bit_order_probe", "validation", BIT_ORDER_PROBE_SPEC),
    ("gate_coverage", "validation", GATE_COVERAGE_SPEC),
)
CIRCUIT_IDS: tuple[str, ...] = tuple(circuit_id for circuit_id, _, _ in CIRCUITS)

BIT_ORDERING: dict[str, Any] = {
    "convention": "qiskit_little_endian",
    "qubit_index_base": 0,
    "rule": "The rightmost character of a bitstring is qubit 0 (clbit 0 for sampled counts).",
    "example": "For 3 qubits with only qubit 0 in |1>, the Qiskit bitstring is '001'.",
    "matlab_note": (
        "MATLAB quantumState.BasisStates put qubit 1 (Qiskit qubit 0) first, so the MATLAB "
        "label for the same state is '100'. Reverse the string to convert in either direction, "
        "and add 1 to every qubit index."
    ),
    "statevector_index": "Index i of amplitudes_* has bitstring format(i, '0{n}b') in Qiskit order.",
}


def _bitstring(index: int, width: int) -> str:
    return format(index, f"0{width}b") if width else ""


def _measured_bitstring(qubit_bits: str, spec: CircuitSpec) -> str:
    """Map a Qiskit-ordered qubit bitstring to the Qiskit-ordered clbit string Aer would report."""
    num_qubits = spec.num_qubits
    clbits = ["0"] * spec.num_clbits
    for measurement in spec.measurements:
        clbits[measurement.clbit] = qubit_bits[num_qubits - 1 - measurement.qubit]
    return "".join(reversed(clbits))


def exact_results(spec: CircuitSpec) -> dict[str, Any]:
    unmeasured = spec.model_copy(update={"measurements": []})
    statevector = Statevector(build_circuit(unmeasured))
    amplitudes = [complex(value) for value in statevector.data]
    probabilities = [float(value) for value in statevector.probabilities()]
    bitstrings = [_bitstring(index, spec.num_qubits) for index in range(len(amplitudes))]

    measured: dict[str, float] = {}
    for bits, probability in zip(bitstrings, probabilities):
        key = _measured_bitstring(bits, spec)
        measured[key] = measured.get(key, 0.0) + probability
    measured_keys = sorted(measured)

    return {
        "method": "qiskit.quantum_info.Statevector",
        "measurements_removed": True,
        "bitstrings": bitstrings,
        "probabilities": probabilities,
        "amplitudes_real": [value.real for value in amplitudes],
        "amplitudes_imag": [value.imag for value in amplitudes],
        "measured_bitstrings": measured_keys,
        "measured_probabilities": [measured[key] for key in measured_keys],
    }


def sampled_results(spec: CircuitSpec, *, shots: int, seed: int) -> dict[str, Any]:
    output, _ = simulate_spec(spec, shots=shots, seed=seed)
    bitstrings = sorted(output.counts)
    counts = [output.counts[key] for key in bitstrings]
    return {
        "method": "qiskit_aer.AerSimulator",
        "shots": shots,
        "seed_simulator": seed,
        "bitstrings": bitstrings,
        "counts": counts,
        "probabilities": [count / shots for count in counts],
    }


def versions() -> dict[str, str]:
    return {
        "qiskit": qiskit.__version__,
        "qiskit_aer": qiskit_aer.__version__,
        "python": platform.python_version(),
    }


def export_circuit(
    circuit_id: str,
    source: str,
    raw_spec: dict[str, Any],
    *,
    shots: int,
    seed: int,
) -> dict[str, Any]:
    spec = normalize_spec(raw_spec, max_qubits=16, max_gates=128)
    public = spec.public_dict()
    return {
        "schema_version": SCHEMA_VERSION,
        "circuit_id": circuit_id,
        "circuit_name": spec.circuit_name,
        "source": source,
        "num_qubits": spec.num_qubits,
        "num_clbits": spec.num_clbits,
        "spec": public,
        "gate_sequence": [gate.gate for gate in spec.gates],
        "measurements": public["measurements"],
        "bit_ordering": BIT_ORDERING,
        "exact": exact_results(spec),
        "sampled": sampled_results(spec, shots=shots, seed=seed),
        "versions": versions(),
        "generated_by": COMMAND,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def export_all(
    output_dir: Path,
    *,
    circuit_ids: Sequence[str] = CIRCUIT_IDS,
    shots: int = DEFAULT_SHOTS,
    seed: int = DEFAULT_SEED,
) -> list[Path]:
    unknown = sorted(set(circuit_ids) - set(CIRCUIT_IDS))
    if unknown:
        raise ValueError(f"unknown circuit id(s): {', '.join(unknown)}")
    if shots < 1:
        raise ValueError("shots must be at least 1")
    output_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    entries: list[dict[str, Any]] = []
    for circuit_id, source, raw_spec in CIRCUITS:
        if circuit_id not in circuit_ids:
            continue
        payload = export_circuit(circuit_id, source, raw_spec, shots=shots, seed=seed)
        path = output_dir / f"{circuit_id}.json"
        write_json(path, payload)
        written.append(path)
        entries.append(
            {
                "circuit_id": circuit_id,
                "circuit_name": payload["circuit_name"],
                "source": source,
                "file": path.name,
            }
        )

    manifest = output_dir / MANIFEST_NAME
    write_json(
        manifest,
        {
            "schema_version": SCHEMA_VERSION,
            "generated_by": COMMAND,
            "shots": shots,
            "seed_simulator": seed,
            "versions": versions(),
            "bit_ordering": BIT_ORDERING,
            "circuits": entries,
        },
    )
    written.append(manifest)
    return written


def default_output_dir() -> Path:
    # backend/app/tools/this_file -> repository root -> matlab/data/qiskit_results
    return Path(__file__).resolve().parents[3] / "matlab" / "data" / "qiskit_results"


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=COMMAND,
        description="Write reference circuit specs and Qiskit results as JSON for MATLAB.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory for the JSON files. Defaults to <repo>/matlab/data/qiskit_results.",
    )
    parser.add_argument("--shots", type=int, default=DEFAULT_SHOTS, help="Aer shots per circuit.")
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED, help="Aer seed_simulator.")
    parser.add_argument(
        "--circuits",
        nargs="+",
        choices=CIRCUIT_IDS,
        default=list(CIRCUIT_IDS),
        help="Subset of circuits to export.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    output_dir = args.output_dir if args.output_dir is not None else default_output_dir()
    try:
        written = export_all(output_dir, circuit_ids=args.circuits, shots=args.shots, seed=args.seed)
    except (ValueError, OSError) as exc:
        print(f"export failed: {exc}", file=sys.stderr)
        return 1
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
