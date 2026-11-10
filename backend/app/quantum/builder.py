"""Build a Qiskit circuit only through the restricted gate map."""

from __future__ import annotations

from collections.abc import Callable

from qiskit import QuantumCircuit

from app.core.errors import CircuitValidationError
from app.schemas.circuit import CircuitSpec, GateSpec

GateBuilder = Callable[[QuantumCircuit, GateSpec], None]


def _id(qc: QuantumCircuit, gate: GateSpec) -> None:
    qc.id(gate.qubits[0])


def _x(qc: QuantumCircuit, gate: GateSpec) -> None:
    qc.x(gate.qubits[0])


def _y(qc: QuantumCircuit, gate: GateSpec) -> None:
    qc.y(gate.qubits[0])


def _z(qc: QuantumCircuit, gate: GateSpec) -> None:
    qc.z(gate.qubits[0])


def _h(qc: QuantumCircuit, gate: GateSpec) -> None:
    qc.h(gate.qubits[0])


def _s(qc: QuantumCircuit, gate: GateSpec) -> None:
    qc.s(gate.qubits[0])


def _t(qc: QuantumCircuit, gate: GateSpec) -> None:
    qc.t(gate.qubits[0])


def _rx(qc: QuantumCircuit, gate: GateSpec) -> None:
    qc.rx(gate.parameter, gate.qubits[0])


def _ry(qc: QuantumCircuit, gate: GateSpec) -> None:
    qc.ry(gate.parameter, gate.qubits[0])


def _rz(qc: QuantumCircuit, gate: GateSpec) -> None:
    qc.rz(gate.parameter, gate.qubits[0])


def _cx(qc: QuantumCircuit, gate: GateSpec) -> None:
    qc.cx(gate.qubits[0], gate.qubits[1])


def _cz(qc: QuantumCircuit, gate: GateSpec) -> None:
    qc.cz(gate.qubits[0], gate.qubits[1])


def _swap(qc: QuantumCircuit, gate: GateSpec) -> None:
    qc.swap(gate.qubits[0], gate.qubits[1])


# User-supplied names never reach getattr/eval. Only these callables run.
GATE_MAP: dict[str, GateBuilder] = {
    "i": _id,
    "x": _x,
    "y": _y,
    "z": _z,
    "h": _h,
    "s": _s,
    "t": _t,
    "rx": _rx,
    "ry": _ry,
    "rz": _rz,
    "cx": _cx,
    "cz": _cz,
    "swap": _swap,
}


def apply_gate(qc: QuantumCircuit, gate: GateSpec) -> None:
    builder = GATE_MAP.get(gate.gate)
    if builder is None:
        raise CircuitValidationError([f"unsupported gate '{gate.gate}'"])
    builder(qc, gate)


def build_circuit(spec: CircuitSpec) -> QuantumCircuit:
    circuit = QuantumCircuit(spec.num_qubits, spec.num_clbits, name=spec.circuit_name)
    for gate in spec.gates:
        apply_gate(circuit, gate)
    for measurement in spec.measurements:
        circuit.measure(measurement.qubit, measurement.clbit)
    return circuit
