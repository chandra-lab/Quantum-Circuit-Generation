"""Feature extraction on the app's reference specs. Expected values are worked out by hand."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from app.quantum.examples import BELL_SPEC, BIT_FLIP_SPEC, GHZ_SPEC, SUPERPOSITION_SPEC
from app.quantum.gates import SUPPORTED_GATES
from app.schemas.circuit import normalize_spec
from research.features import FEATURE_DESCRIPTIONS, FEATURE_NAMES, extract_features, feature_vector

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _features(payload):
    return extract_features(normalize_spec(payload, max_qubits=8, max_gates=128))


def _expected(**nonzero):
    values = {name: 0.0 for name in FEATURE_NAMES}
    for name, value in nonzero.items():
        assert name in values, name
        values[name] = float(value)
    return values


def test_bell_features():
    assert _features(BELL_SPEC) == _expected(
        num_qubits=2, num_clbits=2, total_gates=2, count_h=1, count_cx=1,
        single_qubit_gates=1, two_qubit_gates=1, depth=3, num_measurements=2,
        entangling_gates=1, entangling_pairs=1, largest_entangling_component=2,
        interaction_pairs=1, largest_interaction_component=2, active_qubits=2,
        h_before_cx_control=1,
    )


def test_ghz_features():
    assert _features(GHZ_SPEC) == _expected(
        num_qubits=3, num_clbits=3, total_gates=3, count_h=1, count_cx=2,
        single_qubit_gates=1, two_qubit_gates=2, depth=4, num_measurements=3,
        entangling_gates=2, entangling_pairs=2, largest_entangling_component=3,
        interaction_pairs=2, largest_interaction_component=3, active_qubits=3,
        h_before_cx_control=1,
    )


def test_superposition_features():
    assert _features(SUPERPOSITION_SPEC) == _expected(
        num_qubits=1, num_clbits=1, total_gates=1, count_h=1, single_qubit_gates=1,
        depth=2, num_measurements=1, largest_entangling_component=1,
        largest_interaction_component=1, active_qubits=1,
    )


def test_bit_flip_features():
    assert _features(BIT_FLIP_SPEC) == _expected(
        num_qubits=1, num_clbits=1, total_gates=1, count_x=1, single_qubit_gates=1,
        depth=2, num_measurements=1, largest_entangling_component=1,
        largest_interaction_component=1, active_qubits=1,
    )


def test_swap_counts_as_interaction_not_entanglement():
    payload = {
        "circuit_name": "swap",
        "num_qubits": 3,
        "num_clbits": 0,
        "gates": [
            {"gate": "cx", "qubits": [1, 0]},
            {"gate": "h", "qubits": [0]},
            {"gate": "swap", "qubits": [1, 2]},
            {"gate": "i", "qubits": [2]},
            {"gate": "rz", "qubits": [2], "parameter": 0.5},
        ],
    }
    features = _features(payload)
    assert features["entangling_gates"] == 1
    assert features["largest_entangling_component"] == 2
    assert features["interaction_pairs"] == 2
    assert features["largest_interaction_component"] == 3
    assert features["parametric_gates"] == 1
    assert features["count_i"] == 1
    # The H comes after the CX, and on the CX target, so it does not precede the control.
    assert features["h_before_cx_control"] == 0


def test_every_gate_has_a_count_and_every_feature_is_documented():
    assert {f"count_{gate}" for gate in SUPPORTED_GATES} <= set(FEATURE_NAMES)
    assert list(FEATURE_DESCRIPTIONS) == list(FEATURE_NAMES)
    assert all(FEATURE_DESCRIPTIONS[name] for name in FEATURE_NAMES)
    vector = feature_vector(normalize_spec(BELL_SPEC, max_qubits=8, max_gates=128))
    assert len(vector) == len(FEATURE_NAMES)


def test_app_and_feature_code_do_not_import_torch():
    code = (
        "import sys, app.main, research.features, research.dataset, research.prep, research.metrics; "
        "assert 'torch' not in sys.modules, 'torch imported'"
    )
    result = subprocess.run([sys.executable, "-c", code], cwd=BACKEND_DIR, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
