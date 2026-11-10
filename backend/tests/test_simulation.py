"""Aer simulations for the four canonical circuits. No network calls."""

from __future__ import annotations

import pytest

from app.quantum.examples import BELL_SPEC, BIT_FLIP_SPEC, GHZ_SPEC, SUPERPOSITION_SPEC
from app.quantum.simulator import simulate_spec
from app.quantum.visualizer import circuit_to_svg
from app.schemas.circuit import normalize_spec

SHOTS = 2000
SEED = 1
TOLERANCE = 0.05


def _run(payload):
    spec = normalize_spec(payload, max_qubits=8, max_gates=128)
    output, circuit = simulate_spec(spec, shots=SHOTS, seed=SEED)
    return output, circuit


def test_bell_probabilities():
    output, _circuit = _run(BELL_SPEC)
    assert output.probabilities["00"] == pytest.approx(0.5, abs=TOLERANCE)
    assert output.probabilities["11"] == pytest.approx(0.5, abs=TOLERANCE)
    assert output.probabilities.get("01", 0) < TOLERANCE
    assert output.probabilities.get("10", 0) < TOLERANCE
    assert sum(output.counts.values()) == SHOTS


def test_superposition_probabilities():
    output, _circuit = _run(SUPERPOSITION_SPEC)
    assert output.probabilities["0"] == pytest.approx(0.5, abs=TOLERANCE)
    assert output.probabilities["1"] == pytest.approx(0.5, abs=TOLERANCE)


def test_bit_flip_is_deterministic():
    output, _circuit = _run(BIT_FLIP_SPEC)
    assert output.counts == {"1": SHOTS}
    assert output.probabilities["1"] == pytest.approx(1.0, abs=0.02)


def test_ghz_probabilities():
    output, circuit = _run(GHZ_SPEC)
    assert output.probabilities["000"] == pytest.approx(0.5, abs=TOLERANCE)
    assert output.probabilities["111"] == pytest.approx(0.5, abs=TOLERANCE)
    assert output.probabilities.get("001", 0) < TOLERANCE
    assert circuit.num_qubits == 3


def test_probabilities_match_counts_over_shots():
    output, _circuit = _run(BELL_SPEC)
    for bitstring, count in output.counts.items():
        assert output.probabilities[bitstring] == round(count / SHOTS, 6)


def test_svg_comes_from_the_built_circuit():
    _output, circuit = _run(BELL_SPEC)
    svg = circuit_to_svg(circuit)
    assert svg.startswith("<svg")
    assert "Bell State" in svg or len(svg) > 500


def test_simulation_requires_measurements():
    spec = normalize_spec(
        {
            "circuit_name": "No measure",
            "num_qubits": 1,
            "num_clbits": 0,
            "gates": [{"gate": "h", "qubits": [0]}],
            "measurements": [],
            "description": "State prep only.",
        },
        max_qubits=8,
        max_gates=128,
    )
    with pytest.raises(Exception) as caught:
        simulate_spec(spec, shots=10, seed=SEED)
    assert getattr(caught.value, "code", "") == "measurements_required"
