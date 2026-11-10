"""Canonical circuits used by tests and the reference-circuit UI.

These are predefined specs, not language-model output.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.schemas.circuit import CircuitSpec, normalize_spec

BELL_SPEC: dict[str, Any] = {
    "circuit_name": "Bell State",
    "num_qubits": 2,
    "num_clbits": 2,
    "gates": [
        {"gate": "h", "qubits": [0]},
        {"gate": "cx", "qubits": [0, 1]},
    ],
    "measurements": [
        {"qubit": 0, "clbit": 0},
        {"qubit": 1, "clbit": 1},
    ],
    "description": "Creates an entangled Bell state.",
}

SUPERPOSITION_SPEC: dict[str, Any] = {
    "circuit_name": "Superposition",
    "num_qubits": 1,
    "num_clbits": 1,
    "gates": [{"gate": "h", "qubits": [0]}],
    "measurements": [{"qubit": 0, "clbit": 0}],
    "description": "Applies a Hadamard gate to create an equal superposition, then measures.",
}

GHZ_SPEC: dict[str, Any] = {
    "circuit_name": "GHZ State",
    "num_qubits": 3,
    "num_clbits": 3,
    "gates": [
        {"gate": "h", "qubits": [0]},
        {"gate": "cx", "qubits": [0, 1]},
        {"gate": "cx", "qubits": [0, 2]},
    ],
    "measurements": [
        {"qubit": 0, "clbit": 0},
        {"qubit": 1, "clbit": 1},
        {"qubit": 2, "clbit": 2},
    ],
    "description": "Prepares a three-qubit GHZ state and measures all qubits.",
}

BIT_FLIP_SPEC: dict[str, Any] = {
    "circuit_name": "Bit Flip",
    "num_qubits": 1,
    "num_clbits": 1,
    "gates": [{"gate": "x", "qubits": [0]}],
    "measurements": [{"qubit": 0, "clbit": 0}],
    "description": "Flips |0> to |1> with an X gate and measures.",
}


@dataclass(frozen=True)
class ExamplePrompt:
    id: str
    label: str
    prompt: str
    description: str
    runnable_without_llm: bool
    spec: dict[str, Any] | None


EXAMPLE_PROMPTS: tuple[ExamplePrompt, ...] = (
    ExamplePrompt(
        id="bell",
        label="Bell state",
        prompt="Generate a Bell State using two qubits.",
        description="Two qubits, Hadamard on qubit 0, CNOT from 0 to 1, measure both.",
        runnable_without_llm=True,
        spec=BELL_SPEC,
    ),
    ExamplePrompt(
        id="superposition",
        label="Superposition",
        prompt="Create a quantum superposition using a Hadamard gate.",
        description="One qubit, Hadamard, then measure.",
        runnable_without_llm=True,
        spec=SUPERPOSITION_SPEC,
    ),
    ExamplePrompt(
        id="ghz",
        label="GHZ state (three qubits)",
        prompt=(
            "Create a quantum circuit with three qubits that prepares a GHZ state: "
            "Hadamard on qubit 0, CNOT from 0 to 1, CNOT from 0 to 2, and measure all three qubits."
        ),
        description="Three-qubit GHZ state: H on 0, CNOT 0→1, CNOT 0→2, measure all.",
        runnable_without_llm=True,
        spec=GHZ_SPEC,
    ),
    ExamplePrompt(
        id="x-h-cnot",
        label="X, H, and CNOT",
        prompt="Apply X, H, and CNOT gates to a quantum circuit.",
        description="Open-ended prompt for the language model. No predefined reference circuit.",
        runnable_without_llm=False,
        spec=None,
    ),
    ExamplePrompt(
        id="measurement",
        label="Measurement circuit",
        prompt="Create a quantum measurement circuit.",
        description="Open-ended prompt for the language model. No predefined reference circuit.",
        runnable_without_llm=False,
        spec=None,
    ),
    ExamplePrompt(
        id="bit-flip",
        label="Quantum bit flip",
        prompt=(
            "Quantum bit flip: prepare one qubit in the zero state, apply a single X gate, "
            "and measure that qubit."
        ),
        description="One qubit, X, then measure. The outcome is |1>.",
        runnable_without_llm=True,
        spec=BIT_FLIP_SPEC,
    ),
)


def validated_example_spec(spec: dict[str, Any]) -> CircuitSpec:
    return normalize_spec(spec, max_qubits=16, max_gates=128)


def example_catalog() -> list[dict[str, Any]]:
    catalog: list[dict[str, Any]] = []
    for example in EXAMPLE_PROMPTS:
        spec = validated_example_spec(example.spec).public_dict() if example.spec else None
        catalog.append(
            {
                "id": example.id,
                "label": example.label,
                "prompt": example.prompt,
                "description": example.description,
                "runnable_without_llm": example.runnable_without_llm,
                "source": "reference" if example.runnable_without_llm else None,
                "spec": spec,
            }
        )
    return catalog
