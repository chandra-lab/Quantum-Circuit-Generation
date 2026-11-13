from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

import compare
import matlab_convention_sim as msim

EXPORT_DIR = Path(__file__).resolve().parents[2] / "data" / "qiskit_results"
EXPORT_FILES = sorted(p for p in EXPORT_DIR.glob("*.json") if p.name != "manifest.json")
ASYMMETRIC = {"bit_order_probe", "gate_coverage"}


def load(name: str) -> dict:
    return json.loads((EXPORT_DIR / f"{name}.json").read_text(encoding="utf-8"))


# Bit-order mapping


@pytest.mark.parametrize(
    ("matlab", "qiskit"),
    [("100", "001"), ("110", "011"), ("01", "10"), ("1", "1"), ("0011", "1100"), ("", "")],
)
def test_label_mapping_reverses_the_string(matlab: str, qiskit: str) -> None:
    assert compare.matlab_to_qiskit_label(matlab) == qiskit
    assert compare.qiskit_to_matlab_label(qiskit) == matlab


def test_label_mapping_is_an_involution() -> None:
    for label in msim.basis_states(4):
        assert compare.matlab_to_qiskit_label(compare.qiskit_to_matlab_label(label)) == label


@pytest.mark.parametrize("bad", ["012", "|01>", "ab", None])
def test_label_mapping_rejects_non_binary_labels(bad) -> None:
    with pytest.raises(ValueError):
        compare.matlab_to_qiskit_label(bad)


def test_qubit_zero_in_one_state_matches_both_conventions() -> None:
    # Qiskit qubit 0 is MATLAB qubit 1. X on it gives Qiskit "001" and MATLAB "100".
    probs = msim.simulate_spec({"num_qubits": 3, "gates": [{"gate": "x", "qubits": [0]}]})
    assert probs["100"] == pytest.approx(1.0)
    assert compare.remap_labels(probs, compare.matlab_to_qiskit_label)["001"] == pytest.approx(1.0)


def test_reversed_order_case_is_fixed_by_the_mapping() -> None:
    export = load("bit_order_probe")
    matlab_probs = msim.simulate_spec(export["spec"])
    assert matlab_probs["100"] == pytest.approx(0.75)

    unmapped = compare.compare_distributions(compare.export_exact(export), matlab_probs)
    assert unmapped["max_abs_error"] == pytest.approx(0.75)
    assert not compare.exact_passes(unmapped)

    mapped = compare.compare_matlab_exact(export, matlab_probs)
    assert mapped["passed"]
    assert mapped["max_abs_error"] < 1e-12


@pytest.mark.parametrize(
    ("label", "measurements", "num_clbits", "expected"),
    [
        ("10", [{"qubit": 0, "clbit": 1}, {"qubit": 1, "clbit": 0}], 2, "10"),
        ("10", [{"qubit": 0, "clbit": 0}, {"qubit": 1, "clbit": 1}], 2, "01"),
        ("110", [{"qubit": 0, "clbit": 0}, {"qubit": 1, "clbit": 1}, {"qubit": 2, "clbit": 2}], 3, "011"),
        ("011", [{"qubit": 2, "clbit": 0}], 2, "01"),
        ("111", [{"qubit": 1, "clbit": 0}], 1, "1"),
    ],
)
def test_matlab_label_to_clbits(label, measurements, num_clbits, expected) -> None:
    assert compare.matlab_label_to_clbits(label, measurements, num_clbits) == expected


# Metrics


def test_identical_distributions_have_zero_distance() -> None:
    metrics = compare.compare_distributions({"00": 0.5, "11": 0.5}, {"11": 0.5, "00": 0.5})
    assert metrics["states"] == ["00", "11"]
    assert metrics["max_abs_error"] == 0
    assert metrics["total_variation"] == 0
    assert metrics["hellinger"] == 0
    assert metrics["kl_divergence"] == pytest.approx(0, abs=1e-15)


def test_disjoint_distributions_have_maximum_distance() -> None:
    metrics = compare.compare_distributions({"0": 1.0}, {"1": 1.0})
    assert metrics["total_variation"] == pytest.approx(1.0)
    assert metrics["hellinger"] == pytest.approx(1.0)
    assert math.isfinite(metrics["kl_divergence"])
    assert metrics["kl_divergence"] > 20


def test_hand_computed_metrics() -> None:
    p = {"00": 0.5, "01": 0.25, "11": 0.25}
    q = {"00": 0.4, "10": 0.1, "11": 0.5}
    metrics = compare.compare_distributions(p, q, epsilon=0.0 + 1e-300)
    assert metrics["states"] == ["00", "01", "10", "11"]
    assert metrics["abs_diff"] == pytest.approx([0.1, 0.25, 0.1, 0.25])
    assert metrics["max_abs_error"] == pytest.approx(0.25)
    assert metrics["total_variation"] == pytest.approx(0.35)
    hellinger = math.sqrt(
        0.5 * ((math.sqrt(0.5) - math.sqrt(0.4)) ** 2 + 0.25 + 0.1 + (math.sqrt(0.25) - math.sqrt(0.5)) ** 2)
    )
    assert metrics["hellinger"] == pytest.approx(hellinger)


def test_kl_uses_epsilon_smoothing() -> None:
    p = {"0": 0.5, "1": 0.5}
    q = {"0": 1.0}
    eps = 1e-12
    metrics = compare.compare_distributions(p, q, epsilon=eps)
    ps = [(0.5 + eps) / (1 + 2 * eps)] * 2
    qs = [(1 + eps) / (1 + 2 * eps), eps / (1 + 2 * eps)]
    expected = sum(a * math.log(a / b) for a, b in zip(ps, qs))
    assert metrics["kl_divergence"] == pytest.approx(expected)


def test_metrics_are_symmetric_where_expected() -> None:
    p = {"00": 0.7, "11": 0.3}
    q = {"00": 0.6, "01": 0.4}
    a, b = compare.compare_distributions(p, q), compare.compare_distributions(q, p)
    assert a["total_variation"] == pytest.approx(b["total_variation"])
    assert a["hellinger"] == pytest.approx(b["hellinger"])
    assert a["max_abs_error"] == pytest.approx(b["max_abs_error"])


def test_exact_tolerance_boundary() -> None:
    assert compare.exact_passes({"max_abs_error": 1e-10})
    assert not compare.exact_passes({"max_abs_error": 2e-10})


@pytest.mark.parametrize(
    ("x", "k", "expected"),
    [
        (3.841458820694124, 1, 0.05),
        (0.0, 3, 1.0),
        (2.0, 2, math.exp(-1.0)),
        (10.0, 2, math.exp(-5.0)),
        (11.070497693516351, 5, 0.05),
        (24.321886347856854, 7, 0.001),
        (0.5, 9, 0.99996956625884),
    ],
)
def test_chi2_sf_matches_known_values(x: float, k: int, expected: float) -> None:
    assert compare.chi2_sf(x, k) == pytest.approx(expected, rel=1e-8, abs=1e-12)


def test_goodness_of_fit_passes_for_expected_counts() -> None:
    result = compare.chi_square_goodness_of_fit({"00": 500, "11": 500}, {"00": 0.5, "11": 0.5})
    assert result["statistic"] == 0
    assert result["dof"] == 1
    assert result["passed"]


def test_goodness_of_fit_fails_on_impossible_outcome() -> None:
    result = compare.chi_square_goodness_of_fit({"00": 499, "01": 1, "11": 500}, {"00": 0.5, "11": 0.5})
    assert result["impossible_outcomes"] == ["01"]
    assert not result["passed"]


def test_goodness_of_fit_fails_on_biased_counts() -> None:
    result = compare.chi_square_goodness_of_fit({"0": 700, "1": 300}, {"0": 0.5, "1": 0.5})
    assert result["p_value"] < 1e-10
    assert not result["passed"]


def test_goodness_of_fit_deterministic_circuit_has_zero_dof() -> None:
    result = compare.chi_square_goodness_of_fit({"1": 100}, {"0": 0.0, "1": 1.0})
    assert result["dof"] == 0
    assert result["passed"]


def test_homogeneity() -> None:
    same = compare.chi_square_homogeneity({"0": 500, "1": 500}, {"0": 510, "1": 490})
    assert same["passed"]
    different = compare.chi_square_homogeneity({"0": 900, "1": 100}, {"0": 100, "1": 900})
    assert not different["passed"]


# Fixture shared with matlab.unittest


def _assert_close(actual, expected) -> None:
    if isinstance(expected, dict):
        assert set(actual) == set(expected)
        for key in expected:
            _assert_close(actual[key], expected[key])
    elif isinstance(expected, list):
        assert len(actual) == len(expected)
        for a, e in zip(actual, expected):
            _assert_close(a, e)
    elif isinstance(expected, float):
        assert actual == pytest.approx(expected, rel=1e-12, abs=1e-15)
    else:
        assert actual == expected


def test_matlab_fixture_is_up_to_date() -> None:
    committed = json.loads(compare.FIXTURE_PATH.read_text(encoding="utf-8"))
    _assert_close(json.loads(json.dumps(compare.build_fixture())), committed)


def test_fixture_reversed_case_differs_until_mapped() -> None:
    cases = {case["name"]: case for case in compare.build_fixture()["metric_cases"]}
    assert cases["reversed_unmapped"]["expected"]["max_abs_error"] == pytest.approx(0.75)
    assert cases["reversed_mapped"]["expected"]["max_abs_error"] == 0


def test_fixture_label_and_clbit_cases_agree_with_functions() -> None:
    fixture = compare.build_fixture()
    for case in fixture["label_cases"]:
        assert compare.matlab_to_qiskit_label(case["matlab"]) == case["qiskit"]
    for case in fixture["clbit_cases"]:
        assert (
            compare.matlab_label_to_clbits(case["matlab"], case["measurements"], case["num_clbits"])
            == case["qiskit_clbits"]
        )


# Committed Qiskit exports, run through the MATLAB-convention simulator


def test_committed_exports_exist() -> None:
    names = {p.stem for p in EXPORT_FILES}
    assert {"bell", "superposition", "ghz", "bit_flip"} <= names
    assert ASYMMETRIC <= names


@pytest.mark.parametrize("path", EXPORT_FILES, ids=lambda p: p.stem)
def test_matlab_convention_probabilities_match_export(path: Path) -> None:
    export = json.loads(path.read_text(encoding="utf-8"))
    result = compare.compare_matlab_exact(export, msim.simulate_spec(export["spec"]))
    assert result["passed"], result["max_abs_error"]


@pytest.mark.parametrize("name", sorted(ASYMMETRIC))
def test_skipping_the_mapping_fails_on_asymmetric_exports(name: str) -> None:
    export = load(name)
    unmapped = compare.compare_distributions(compare.export_exact(export), msim.simulate_spec(export["spec"]))
    assert not compare.exact_passes(unmapped)


@pytest.mark.parametrize("name", ["bell", "ghz"])
def test_symmetric_exports_cannot_detect_a_reversal(name: str) -> None:
    # Documented limitation: these pass with or without the mapping.
    export = load(name)
    unmapped = compare.compare_distributions(compare.export_exact(export), msim.simulate_spec(export["spec"]))
    assert compare.exact_passes(unmapped)


@pytest.mark.parametrize("path", EXPORT_FILES, ids=lambda p: p.stem)
def test_matlab_labels_map_to_measured_clbit_distribution(path: Path) -> None:
    export = json.loads(path.read_text(encoding="utf-8"))
    probs = msim.simulate_spec(export["spec"])
    mapped: dict[str, float] = {}
    for label, p in probs.items():
        key = compare.matlab_label_to_clbits(label, export["measurements"], export["num_clbits"])
        mapped[key] = mapped.get(key, 0.0) + p
    metrics = compare.compare_distributions(compare.export_measured_exact(export), mapped)
    assert metrics["max_abs_error"] < 1e-12


@pytest.mark.parametrize("path", EXPORT_FILES, ids=lambda p: p.stem)
def test_exported_aer_counts_pass_goodness_of_fit(path: Path) -> None:
    export = json.loads(path.read_text(encoding="utf-8"))
    result = compare.chi_square_goodness_of_fit(
        compare.export_counts(export), compare.export_measured_exact(export)
    )
    assert result["passed"], result


def test_matlab_counts_to_clbits_uses_measurement_map() -> None:
    export = {"measurements": [{"qubit": 0, "clbit": 0}, {"qubit": 1, "clbit": 1}], "num_clbits": 2}
    assert compare.matlab_counts_to_clbits(export, {"10": 30, "11": 70}) == {"01": 30, "11": 70}
