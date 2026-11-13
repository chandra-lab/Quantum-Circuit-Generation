"""Fixed-length numeric features computed from a validated circuit spec.

Feature order is ``FEATURE_NAMES`` and never depends on the data. Each feature is
described in ``FEATURE_DESCRIPTIONS``. Depth comes from the app's own Qiskit
builder (``build_circuit(spec).depth()``), so it counts measurements as layers.
"""

from __future__ import annotations

from typing import Any

from app.quantum.builder import build_circuit
from app.quantum.gates import PARAMETRIC_GATES, SUPPORTED_GATES, TWO_QUBIT_GATES
from app.schemas.circuit import CircuitSpec, normalize_spec

GATE_ORDER: tuple[str, ...] = tuple(sorted(SUPPORTED_GATES))
ENTANGLING_GATES = frozenset({"cx", "cz"})

FEATURE_DESCRIPTIONS: dict[str, str] = {
    "num_qubits": "Size of the quantum register.",
    "num_clbits": "Size of the classical register.",
    "total_gates": "Number of entries in `gates`, identity gates included. Measurements are not gates.",
    **{f"count_{name}": f"Number of `{name}` gates." for name in GATE_ORDER},
    "single_qubit_gates": "Gates acting on one qubit (i, x, y, z, h, s, t, rx, ry, rz).",
    "two_qubit_gates": "Gates acting on two qubits (cx, cz, swap).",
    "parametric_gates": "Rotation gates rx, ry, rz.",
    "depth": "QuantumCircuit.depth() of the circuit built by app.quantum.builder.build_circuit, measurements included.",
    "num_measurements": "Entries in `measurements`.",
    "entangling_gates": "cx plus cz gates. SWAP is excluded because it does not create entanglement.",
    "entangling_pairs": "Distinct unordered qubit pairs joined by a cx or cz.",
    "largest_entangling_component": "Qubits in the largest connected component of the graph whose edges are cx/cz pairs. An isolated qubit is a component of size 1.",
    "interaction_pairs": "Distinct unordered qubit pairs joined by any two-qubit gate (cx, cz, swap).",
    "largest_interaction_component": "Qubits in the largest connected component of the cx/cz/swap interaction graph.",
    "active_qubits": "Qubits touched by at least one non-identity gate.",
    "h_before_cx_control": "1 if some cx has its control qubit acted on by an h earlier in the gate list, else 0.",
}

FEATURE_NAMES: tuple[str, ...] = tuple(FEATURE_DESCRIPTIONS)


def _largest_component(num_qubits: int, pairs: set[tuple[int, int]]) -> int:
    parent = list(range(num_qubits))

    def find(node: int) -> int:
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for a, b in pairs:
        parent[find(a)] = find(b)
    sizes: dict[int, int] = {}
    for qubit in range(num_qubits):
        root = find(qubit)
        sizes[root] = sizes.get(root, 0) + 1
    return max(sizes.values(), default=0)


def extract_features(spec: CircuitSpec) -> dict[str, float]:
    counts = {name: 0 for name in GATE_ORDER}
    entangling: set[tuple[int, int]] = set()
    interaction: set[tuple[int, int]] = set()
    active: set[int] = set()
    hadamard_seen: set[int] = set()
    h_before_cx = 0

    for gate in spec.gates:
        counts[gate.gate] += 1
        if gate.gate != "i":
            active.update(gate.qubits)
        if gate.gate == "h":
            hadamard_seen.add(gate.qubits[0])
        if gate.gate == "cx" and gate.qubits[0] in hadamard_seen:
            h_before_cx = 1
        if gate.gate in TWO_QUBIT_GATES:
            pair = (min(gate.qubits), max(gate.qubits))
            interaction.add(pair)
            if gate.gate in ENTANGLING_GATES:
                entangling.add(pair)

    two_qubit = sum(counts[name] for name in TWO_QUBIT_GATES)
    values: dict[str, float] = {
        "num_qubits": spec.num_qubits,
        "num_clbits": spec.num_clbits,
        "total_gates": len(spec.gates),
        **{f"count_{name}": counts[name] for name in GATE_ORDER},
        "single_qubit_gates": len(spec.gates) - two_qubit,
        "two_qubit_gates": two_qubit,
        "parametric_gates": sum(counts[name] for name in PARAMETRIC_GATES),
        "depth": build_circuit(spec).depth(),
        "num_measurements": len(spec.measurements),
        "entangling_gates": sum(counts[name] for name in ENTANGLING_GATES),
        "entangling_pairs": len(entangling),
        "largest_entangling_component": _largest_component(spec.num_qubits, entangling),
        "interaction_pairs": len(interaction),
        "largest_interaction_component": _largest_component(spec.num_qubits, interaction),
        "active_qubits": len(active),
        "h_before_cx_control": h_before_cx,
    }
    return {name: float(values[name]) for name in FEATURE_NAMES}


def feature_vector(spec: CircuitSpec) -> list[float]:
    features = extract_features(spec)
    return [features[name] for name in FEATURE_NAMES]


def feature_matrix(specs: list[dict[str, Any]], *, max_qubits: int, max_gates: int) -> list[list[float]]:
    return [
        feature_vector(normalize_spec(spec, max_qubits=max_qubits, max_gates=max_gates))
        for spec in specs
    ]
