"""Learner-mode explanations. Deterministic and independent of Groq."""

from __future__ import annotations

import copy
import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.quantum.examples import BELL_SPEC, BIT_FLIP_SPEC, GHZ_SPEC, SUPERPOSITION_SPEC
from app.schemas.circuit import CircuitSpec
from app.services.explanation import (
    classify_pattern,
    explain_error_detail,
    explain_errors,
    explain_result,
)
from tests.conftest import FakeLLM, make_settings

BIT_ORDER_PHRASE = "Qiskit writes classical bit 0 as the rightmost character"


def spec_of(payload: dict) -> CircuitSpec:
    return CircuitSpec.model_validate(payload)


def joined(explanation: dict) -> str:
    parts: list[str] = []
    for value in explanation.values():
        if isinstance(value, list):
            parts.extend(value)
        elif isinstance(value, str):
            parts.append(value)
    return "\n".join(parts)


def test_bell_explanation():
    explanation = explain_result(spec_of(BELL_SPEC), shots=1000, counts={"00": 503, "11": 497})
    assert explanation["pattern"] == "bell"
    assert '"Bell State"' in explanation["overview"]
    assert "Creates an entangled Bell state." in explanation["overview"]
    assert explanation["steps"] == [
        "Step 1: H (Hadamard) on qubit 0 puts it in an equal superposition of 0 and 1.",
        "Step 2: CX (CNOT) with control 0 and target 1 flips qubit 1 when qubit 0 is 1, which entangles them.",
    ]
    assert "Measuring qubit 0 reads it as 0 or 1 and stores that in classical bit 0." in explanation["measurements"]
    assert BIT_ORDER_PHRASE in explanation["bit_order"]
    assert "rightmost character is qubit 0" in explanation["bit_order"]
    outcome = " ".join(explanation["outcome"])
    assert '"00" appeared 503 times out of 1000 (50.3%)' in outcome
    assert '"11" appeared 497 times out of 1000 (49.7%)' in outcome
    assert "shot noise" in outcome
    assert "1000 samples" in outcome
    assert explanation["key_idea"].startswith("Key idea: entanglement (a Bell state)")
    assert explanation["validation"].startswith("Validation passed")
    assert explanation["errors"] == []


def test_superposition_explanation():
    explanation = explain_result(spec_of(SUPERPOSITION_SPEC), shots=2000, counts={"0": 1013, "1": 987})
    assert explanation["pattern"] == "superposition"
    assert "equal superposition of 0 and 1" in explanation["steps"][0]
    outcome = " ".join(explanation["outcome"])
    assert "run 2000 times" in outcome
    assert "(50.6%)" in outcome
    assert "(49.4%)" in outcome
    assert "shot noise" in outcome
    assert explanation["key_idea"].startswith("Key idea: superposition")
    assert BIT_ORDER_PHRASE in explanation["bit_order"]


def test_bit_flip_explanation():
    explanation = explain_result(spec_of(BIT_FLIP_SPEC), shots=100, counts={"1": 100})
    assert explanation["pattern"] == "bit_flip"
    assert "0 becomes 1" in explanation["steps"][0]
    outcome = " ".join(explanation["outcome"])
    assert '"1" appeared 100 times out of 100 (100.0%)' in outcome
    assert "certain" in outcome
    assert "shot noise" not in outcome
    assert explanation["key_idea"].startswith("Key idea: deterministic bit flip")
    assert BIT_ORDER_PHRASE in explanation["bit_order"]


def test_ghz_explanation():
    counts = {"000": 1012, "111": 988}
    explanation = explain_result(spec_of(GHZ_SPEC), shots=2000, counts=counts)
    assert explanation["pattern"] == "ghz"
    assert len(explanation["steps"]) == 3
    assert "control 0 and target 2" in explanation["steps"][2]
    assert "entangles them" in explanation["steps"][2]
    outcome = " ".join(explanation["outcome"])
    assert '"000" appeared 1012 times out of 2000 (50.6%)' in outcome
    assert '"111" appeared 988 times out of 2000 (49.4%)' in outcome
    assert 'Only "000" and "111" appear' in outcome
    assert "shot noise" in outcome
    assert "3 qubits" in explanation["key_idea"]
    assert '"001" means classical bit 0 is 1' in explanation["bit_order"]


def test_unrecognised_circuit_gets_generic_summary():
    payload = {
        "circuit_name": "Rotation",
        "num_qubits": 1,
        "num_clbits": 1,
        "gates": [{"gate": "ry", "qubits": [0], "parameter": 1.0}],
        "measurements": [{"qubit": 0, "clbit": 0}],
        "description": "",
    }
    explanation = explain_result(spec_of(payload), shots=1000, counts={"0": 770, "1": 230})
    assert explanation["pattern"] is None
    assert explanation["key_idea"].startswith("In short:")
    assert "about 57 degrees" in explanation["steps"][0]
    assert "(77.0%)" in " ".join(explanation["outcome"])


def test_cx_without_superposition_does_not_claim_entanglement():
    payload = copy.deepcopy(BELL_SPEC)
    payload["gates"] = [{"gate": "x", "qubits": [0]}, {"gate": "cx", "qubits": [0, 1]}]
    explanation = explain_result(spec_of(payload), shots=10, counts={"11": 10})
    assert "entangles" not in explanation["steps"][1]
    assert classify_pattern(spec_of(payload)) is None


def test_many_outcomes_are_summarised():
    payload = {
        "circuit_name": "Three Hadamards",
        "num_qubits": 3,
        "num_clbits": 3,
        "gates": [{"gate": "h", "qubits": [q]} for q in range(3)],
        "measurements": [{"qubit": q, "clbit": q} for q in range(3)],
    }
    counts = {format(i, "03b"): 125 for i in range(8)}
    explanation = explain_result(spec_of(payload), shots=1000, counts=counts)
    assert explanation["pattern"] == "superposition"
    assert "4 other outcome(s) appeared 500 times in total (50.0%)" in " ".join(explanation["outcome"])


def test_invalid_circuit_errors_are_explained():
    explanation = explain_errors(
        [
            "gates.0.gate: unsupported gate 'toffoli'",
            "gates[1] qubit index 5 is out of range for num_qubits=2",
            "measurements[1] clbit 0 is already used",
        ]
    )
    assert explanation["validation"].startswith("Validation failed")
    assert "nothing was simulated" in explanation["overview"]
    assert explanation["errors"][0].startswith('The gate "toffoli" is not one this app can run.')
    assert "uses qubit 5, but the circuit only has 2 qubit(s)" in explanation["errors"][1]
    assert "Two measurements write to classical bit 0" in explanation["errors"][2]


@pytest.mark.parametrize(
    "detail, phrase",
    [
        ("gates.0: Value error, gate 'cx' requires distinct qubits", "same qubit twice"),
        ("gates.0: gate 'rx' requires a finite numeric parameter", "needs an angle"),
        ("num_qubits 20 exceeds MAX_QUBITS (8)", "allows at most 8"),
        ("circuit_name: Field required", 'field "circuit_name" is missing'),
        ("Simulation requires at least one measurement.", "never measures a qubit"),
        ("something unexpected", "could not translate: something unexpected"),
    ],
)
def test_error_detail_translations(detail, phrase):
    assert phrase in explain_error_detail(detail)


def test_simulate_response_includes_learner_explanation(client):
    response = client.post("/api/circuits/simulate", json={"spec": BELL_SPEC, "shots": 500})
    assert response.status_code == 200
    body = response.json()
    explanation = body["learner_explanation"]
    counts = body["counts"]
    for bitstring, count in counts.items():
        assert f'"{bitstring}" appeared {count} times out of 500 ({count / 5:.1f}%)' in joined(explanation)
    assert explanation["pattern"] == "bell"
    for key in ("spec", "validation", "shots", "counts", "probabilities", "metadata", "visualization"):
        assert key in body


def test_generate_and_simulate_includes_learner_explanation(tmp_path):
    application = create_app(make_settings(tmp_path))
    application.state.llm = FakeLLM([json.dumps(GHZ_SPEC)])
    with TestClient(application) as client:
        response = client.post(
            "/api/circuits/generate-and-simulate",
            json={"prompt": "make a GHZ state", "shots": 300},
        )
    assert response.status_code == 200
    body = response.json()
    assert body["metadata"]["provider"] == "fake"
    assert body["learner_explanation"]["pattern"] == "ghz"
    assert "run 300 times" in " ".join(body["learner_explanation"]["outcome"])


def test_invalid_simulate_returns_learner_explanation(client):
    payload = copy.deepcopy(BELL_SPEC)
    payload["gates"][0]["gate"] = "toffoli"
    response = client.post("/api/circuits/simulate", json={"spec": payload, "shots": 100})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert body["learner_explanation"]["validation"].startswith("Validation failed")
    assert 'The gate "toffoli"' in body["learner_explanation"]["errors"][0]


def test_missing_measurements_returns_learner_explanation(client):
    payload = copy.deepcopy(BELL_SPEC)
    payload["measurements"] = []
    response = client.post("/api/circuits/simulate", json={"spec": payload, "shots": 100})
    assert response.status_code == 400
    assert "never measures a qubit" in response.json()["learner_explanation"]["errors"][0]


def test_other_errors_have_no_learner_explanation(client):
    response = client.post("/api/circuits/generate", json={"prompt": "Bell state"})
    assert response.status_code == 503
    assert "learner_explanation" not in response.json()
