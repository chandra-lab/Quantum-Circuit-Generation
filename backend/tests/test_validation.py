"""Schema and gate-allowlist tests."""

from __future__ import annotations

import math

import pytest

from app.core.errors import CircuitValidationError
from app.quantum.builder import GATE_MAP, build_circuit
from app.quantum.examples import BELL_SPEC, BIT_FLIP_SPEC, GHZ_SPEC, SUPERPOSITION_SPEC
from app.quantum.gates import SUPPORTED_GATES
from app.schemas.circuit import CircuitSpec, GateSpec, normalize_spec
from app.services.llm.schema import circuit_json_schema


def _parse(payload, max_qubits=8):
    return normalize_spec(payload, max_qubits=max_qubits, max_gates=128)


def test_bell_schema_matches_documented_shape():
    spec = _parse(BELL_SPEC)
    assert spec.public_dict() == BELL_SPEC
    assert spec.gates[0].gate == "h"
    assert spec.gates[1].qubits == [0, 1]


def test_gate_names_are_canonical_lowercase():
    payload = {
        **BELL_SPEC,
        "gates": [
            {"gate": "H", "qubits": [0]},
            {"gate": "CX", "qubits": [0, 1]},
        ],
    }
    spec = _parse(payload)
    assert [gate.gate for gate in spec.gates] == ["h", "cx"]


def test_invalid_qubit_index():
    payload = {
        **SUPERPOSITION_SPEC,
        "gates": [{"gate": "h", "qubits": [5]}],
    }
    with pytest.raises(CircuitValidationError) as caught:
        _parse(payload)
    assert any("out of range" in message for message in caught.value.details)


def test_negative_qubit_index():
    payload = {
        **SUPERPOSITION_SPEC,
        "gates": [{"gate": "h", "qubits": [-1]}],
    }
    with pytest.raises(CircuitValidationError) as caught:
        _parse(payload)
    assert any("out of range" in message for message in caught.value.details)


def test_unsupported_gate():
    payload = {
        **SUPERPOSITION_SPEC,
        "gates": [{"gate": "ccx", "qubits": [0]}],
    }
    with pytest.raises(CircuitValidationError) as caught:
        _parse(payload)
    assert any("unsupported gate" in message for message in caught.value.details)


def test_missing_rotation_parameter():
    payload = {
        "circuit_name": "Rotate",
        "num_qubits": 1,
        "num_clbits": 1,
        "gates": [{"gate": "rx", "qubits": [0]}],
        "measurements": [{"qubit": 0, "clbit": 0}],
        "description": "Missing angle.",
    }
    with pytest.raises(CircuitValidationError) as caught:
        _parse(payload)
    assert any("parameter" in message for message in caught.value.details)


@pytest.mark.parametrize("parameter", [math.nan, math.inf, "pi", True])
def test_invalid_parameter_values(parameter):
    payload = {
        "circuit_name": "Rotate",
        "num_qubits": 1,
        "num_clbits": 1,
        "gates": [{"gate": "rx", "qubits": [0], "parameter": parameter}],
        "measurements": [{"qubit": 0, "clbit": 0}],
        "description": "Bad angle.",
    }
    with pytest.raises(CircuitValidationError) as caught:
        _parse(payload)
    assert any("parameter" in message for message in caught.value.details)


def test_parameter_rejected_on_hadamard():
    payload = {
        **SUPERPOSITION_SPEC,
        "gates": [{"gate": "h", "qubits": [0], "parameter": 1.0}],
    }
    with pytest.raises(CircuitValidationError) as caught:
        _parse(payload)
    assert any("does not take a parameter" in message for message in caught.value.details)


def test_cx_control_must_differ_from_target():
    payload = {
        **BELL_SPEC,
        "gates": [{"gate": "cx", "qubits": [0, 0]}],
    }
    with pytest.raises(CircuitValidationError) as caught:
        _parse(payload)
    assert any("distinct" in message for message in caught.value.details)


def test_swap_qubits_must_differ():
    payload = {
        "circuit_name": "Swap",
        "num_qubits": 2,
        "num_clbits": 1,
        "gates": [{"gate": "swap", "qubits": [1, 1]}],
        "measurements": [{"qubit": 0, "clbit": 0}],
        "description": "Invalid swap.",
    }
    with pytest.raises(CircuitValidationError) as caught:
        _parse(payload)
    assert any("distinct" in message for message in caught.value.details)


def test_measurement_clbit_collision():
    payload = {
        **BELL_SPEC,
        "measurements": [
            {"qubit": 0, "clbit": 0},
            {"qubit": 1, "clbit": 0},
        ],
    }
    with pytest.raises(CircuitValidationError) as caught:
        _parse(payload)
    assert any("already used" in message for message in caught.value.details)


def test_measurement_clbit_out_of_range():
    payload = {
        **SUPERPOSITION_SPEC,
        "measurements": [{"qubit": 0, "clbit": 3}],
    }
    with pytest.raises(CircuitValidationError) as caught:
        _parse(payload)
    assert any("out of range" in message for message in caught.value.details)


def test_num_qubits_respects_configured_maximum():
    payload = {**SUPERPOSITION_SPEC, "num_qubits": 9, "gates": [{"gate": "h", "qubits": [0]}]}
    with pytest.raises(CircuitValidationError) as caught:
        _parse(payload, max_qubits=8)
    assert any("MAX_QUBITS" in message for message in caught.value.details)


def test_bell_and_superposition_build_expected_operations():
    bell = build_circuit(_parse(BELL_SPEC))
    assert [instruction.operation.name for instruction in bell.data] == [
        "h",
        "cx",
        "measure",
        "measure",
    ]
    superposition = build_circuit(_parse(SUPERPOSITION_SPEC))
    assert [instruction.operation.name for instruction in superposition.data] == ["h", "measure"]
    bit_flip = build_circuit(_parse(BIT_FLIP_SPEC))
    assert [instruction.operation.name for instruction in bit_flip.data] == ["x", "measure"]
    ghz = build_circuit(_parse(GHZ_SPEC))
    assert [instruction.operation.name for instruction in ghz.data] == [
        "h",
        "cx",
        "cx",
        "measure",
        "measure",
        "measure",
    ]


def test_builder_does_not_execute_unknown_gate_names():
    spec = CircuitSpec.model_construct(
        circuit_name="Unsafe",
        num_qubits=1,
        num_clbits=1,
        gates=[GateSpec.model_construct(gate="__import__('os')", qubits=[0], parameter=None)],
        measurements=[],
        description="",
    )
    with pytest.raises(CircuitValidationError):
        build_circuit(spec)
    assert "__import__('os')" not in GATE_MAP


def test_rotation_parameter_is_forwarded():
    spec = _parse(
        {
            "circuit_name": "Rotate",
            "num_qubits": 1,
            "num_clbits": 1,
            "gates": [{"gate": "rx", "qubits": [0], "parameter": 1.2}],
            "measurements": [{"qubit": 0, "clbit": 0}],
            "description": "X rotation.",
        }
    )
    circuit = build_circuit(spec)
    operation = circuit.data[0].operation
    assert operation.name == "rx"
    assert operation.params[0] == pytest.approx(1.2)


def test_llm_schema_enum_matches_gate_map():
    schema = circuit_json_schema()
    enum = set(schema["properties"]["gates"]["items"]["properties"]["gate"]["enum"])
    assert enum == SUPPORTED_GATES
    assert set(GATE_MAP) == SUPPORTED_GATES
