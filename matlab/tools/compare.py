"""Bit-order mapping and distribution metrics for the MATLAB validation workflow.

This is the Python twin of matlab/+qcg/*.m. The formulas, ordering, defaults, and
tolerances here must stay equal to the MATLAB functions named in each docstring.
matlab/tests/fixtures/metric_cases.json is generated from this module and checked by
both pytest and matlab.unittest, so a drift on either side fails a test.

Standard library only, so it runs without the backend environment.

Bit ordering
------------
Qiskit bitstrings are little-endian: the rightmost character is qubit 0.
MATLAB quantumState.BasisStates put qubit 1 first (leftmost), and MATLAB qubit k is
Qiskit qubit k-1. The same basis state is therefore the reversed string:

    Qiskit "001"  (qubit 0 is 1)  <->  MATLAB "100"  (qubit 1 is 1)
"""

from __future__ import annotations

import argparse
import json
import math
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

EXACT_TOLERANCE = 1e-10
KL_EPSILON = 1e-12
SAMPLED_ALPHA = 1e-3

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "metric_cases.json"


def _check_label(label: str) -> str:
    if not isinstance(label, str) or any(ch not in "01" for ch in label):
        raise ValueError(f"bitstring must contain only '0' and '1': {label!r}")
    return label


def matlab_to_qiskit_label(label: str) -> str:
    """MATLAB basis label (qubit 1 first) -> Qiskit bitstring (qubit 0 last). qcg.matlabToQiskitLabel."""
    return _check_label(label)[::-1]


def qiskit_to_matlab_label(label: str) -> str:
    """Qiskit bitstring -> MATLAB basis label. The mapping is its own inverse. qcg.qiskitToMatlabLabel."""
    return _check_label(label)[::-1]


def remap_labels(distribution: Mapping[str, float], mapper) -> dict[str, float]:
    remapped: dict[str, float] = {}
    for label, value in distribution.items():
        key = mapper(label)
        remapped[key] = remapped.get(key, 0.0) + value
    return remapped


def matlab_label_to_clbits(
    label: str,
    measurements: Sequence[Mapping[str, int]],
    num_clbits: int,
) -> str:
    """Measured MATLAB qubit label -> Qiskit clbit string, as Aer would report it. qcg.matlabLabelToClbits.

    ``measurements`` use the exported 0-based Qiskit indices. Unmeasured clbits read 0.
    """
    _check_label(label)
    clbits = ["0"] * num_clbits
    for measurement in measurements:
        qubit = int(measurement["qubit"])
        clbit = int(measurement["clbit"])
        clbits[clbit] = label[qubit]
    return "".join(reversed(clbits))


def align(
    reference: Mapping[str, float],
    candidate: Mapping[str, float],
) -> tuple[list[str], list[float], list[float]]:
    """Union of labels in sorted order, with 0 for a label missing on one side."""
    keys = sorted(set(reference) | set(candidate))
    return keys, [float(reference.get(k, 0.0)) for k in keys], [float(candidate.get(k, 0.0)) for k in keys]


def compare_distributions(
    reference: Mapping[str, float],
    candidate: Mapping[str, float],
    *,
    epsilon: float = KL_EPSILON,
) -> dict[str, Any]:
    """Per-state and summary differences between two distributions. qcg.compareDistributions.

    - abs_diff: |candidate - reference| per state
    - max_abs_error: max of abs_diff
    - total_variation: 0.5 * sum |p - q|
    - hellinger: sqrt(0.5 * sum (sqrt p - sqrt q)^2), in [0, 1]
    - kl_divergence: KL(reference || candidate) after adding epsilon to every state and
      renormalising both sides, so a zero in the candidate does not give infinity
    """
    keys, p, q = align(reference, candidate)
    abs_diff = [abs(b - a) for a, b in zip(p, q)]
    total_variation = 0.5 * sum(abs_diff)
    hellinger = math.sqrt(0.5 * sum((math.sqrt(max(a, 0.0)) - math.sqrt(max(b, 0.0))) ** 2 for a, b in zip(p, q)))
    p_s = [max(a, 0.0) + epsilon for a in p]
    q_s = [max(b, 0.0) + epsilon for b in q]
    p_sum, q_sum = sum(p_s), sum(q_s)
    kl = sum((a / p_sum) * math.log((a / p_sum) / (b / q_sum)) for a, b in zip(p_s, q_s))
    return {
        "states": keys,
        "reference": p,
        "candidate": q,
        "abs_diff": abs_diff,
        "max_abs_error": max(abs_diff) if abs_diff else 0.0,
        "total_variation": total_variation,
        "hellinger": hellinger,
        "kl_divergence": max(kl, 0.0),
        "epsilon": epsilon,
    }


def exact_passes(metrics: Mapping[str, Any], tolerance: float = EXACT_TOLERANCE) -> bool:
    return float(metrics["max_abs_error"]) <= tolerance


def _upper_regularized_gamma(a: float, x: float) -> float:
    """Q(a, x) = Gamma(a, x) / Gamma(a). MATLAB: gammainc(x, a, 'upper')."""
    if x <= 0:
        return 1.0
    if x < a + 1:
        term = 1.0 / a
        total = term
        n = a
        for _ in range(10_000):
            n += 1
            term *= x / n
            total += term
            if abs(term) < abs(total) * 1e-15:
                break
        return max(0.0, 1.0 - total * math.exp(-x + a * math.log(x) - math.lgamma(a)))
    tiny = 1e-300
    b = x + 1 - a
    c = 1 / tiny
    d = 1 / b
    h = d
    for i in range(1, 10_000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = tiny if abs(d) < tiny else d
        c = b + an / c
        c = tiny if abs(c) < tiny else c
        d = 1 / d
        delta = d * c
        h *= delta
        if abs(delta - 1) < 1e-15:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def chi2_sf(statistic: float, dof: int) -> float:
    """Chi-square survival function, P(X >= statistic). MATLAB: gammainc(x/2, k/2, 'upper')."""
    if dof <= 0:
        return 1.0
    return _upper_regularized_gamma(dof / 2.0, statistic / 2.0)


def chi_square_goodness_of_fit(
    counts: Mapping[str, int],
    expected_probabilities: Mapping[str, float],
    *,
    alpha: float = SAMPLED_ALPHA,
    zero_threshold: float = EXACT_TOLERANCE,
) -> dict[str, Any]:
    """Sampled counts against an exact distribution. qcg.chiSquareGoodnessOfFit.

    States with expected probability <= zero_threshold are "impossible". Any count on one
    fails the test outright. The chi-square uses the remaining states, dof = states - 1.
    """
    shots = int(sum(counts.values()))
    possible = sorted(k for k, v in expected_probabilities.items() if v > zero_threshold)
    impossible = sorted(k for k, v in counts.items() if v > 0 and expected_probabilities.get(k, 0.0) <= zero_threshold)
    statistic = 0.0
    for key in possible:
        expected = shots * expected_probabilities[key]
        observed = counts.get(key, 0)
        statistic += (observed - expected) ** 2 / expected
    dof = max(len(possible) - 1, 0)
    p_value = chi2_sf(statistic, dof) if shots > 0 else 1.0
    return {
        "test": "chi_square_goodness_of_fit",
        "shots": shots,
        "statistic": statistic,
        "dof": dof,
        "p_value": p_value,
        "alpha": alpha,
        "impossible_outcomes": impossible,
        "passed": not impossible and p_value >= alpha,
    }


def chi_square_homogeneity(
    counts_a: Mapping[str, int],
    counts_b: Mapping[str, int],
    *,
    alpha: float = SAMPLED_ALPHA,
) -> dict[str, Any]:
    """Two-sample chi-square test that two count tables share one distribution. qcg.chiSquareHomogeneity."""
    keys = sorted(k for k in set(counts_a) | set(counts_b) if counts_a.get(k, 0) + counts_b.get(k, 0) > 0)
    n_a = sum(counts_a.get(k, 0) for k in keys)
    n_b = sum(counts_b.get(k, 0) for k in keys)
    total = n_a + n_b
    statistic = 0.0
    if n_a > 0 and n_b > 0:
        for key in keys:
            column = counts_a.get(key, 0) + counts_b.get(key, 0)
            for observed, row in ((counts_a.get(key, 0), n_a), (counts_b.get(key, 0), n_b)):
                expected = row * column / total
                statistic += (observed - expected) ** 2 / expected
    dof = max(len(keys) - 1, 0)
    p_value = chi2_sf(statistic, dof)
    return {
        "test": "chi_square_homogeneity",
        "shots_a": n_a,
        "shots_b": n_b,
        "statistic": statistic,
        "dof": dof,
        "p_value": p_value,
        "alpha": alpha,
        "passed": p_value >= alpha,
    }


def counts_to_probabilities(counts: Mapping[str, int]) -> dict[str, float]:
    shots = sum(counts.values())
    return {k: v / shots for k, v in counts.items()} if shots else {}


def export_exact(export: Mapping[str, Any]) -> dict[str, float]:
    exact = export["exact"]
    return dict(zip(exact["bitstrings"], exact["probabilities"]))


def export_measured_exact(export: Mapping[str, Any]) -> dict[str, float]:
    exact = export["exact"]
    return dict(zip(exact["measured_bitstrings"], exact["measured_probabilities"]))


def export_counts(export: Mapping[str, Any]) -> dict[str, int]:
    sampled = export["sampled"]
    return dict(zip(sampled["bitstrings"], sampled["counts"]))


def compare_matlab_exact(
    export: Mapping[str, Any],
    matlab_probabilities: Mapping[str, float],
    *,
    tolerance: float = EXACT_TOLERANCE,
) -> dict[str, Any]:
    """MATLAB statevector probabilities keyed by MATLAB labels against the Qiskit export."""
    candidate = remap_labels(matlab_probabilities, matlab_to_qiskit_label)
    metrics = compare_distributions(export_exact(export), candidate)
    metrics["tolerance"] = tolerance
    metrics["passed"] = exact_passes(metrics, tolerance)
    return metrics


def matlab_counts_to_clbits(export: Mapping[str, Any], matlab_counts: Mapping[str, int]) -> dict[str, int]:
    measurements = export["measurements"]
    num_clbits = int(export["num_clbits"])
    mapped: dict[str, int] = {}
    for label, count in matlab_counts.items():
        key = matlab_label_to_clbits(label, measurements, num_clbits)
        mapped[key] = mapped.get(key, 0) + int(count)
    return mapped


def _fixture_case(name: str, reference: dict[str, float], candidate: dict[str, float]) -> dict[str, Any]:
    metrics = compare_distributions(reference, candidate)
    return {
        "name": name,
        "reference": reference,
        "candidate": candidate,
        "expected": {
            key: metrics[key]
            for key in ("states", "abs_diff", "max_abs_error", "total_variation", "hellinger", "kl_divergence")
        },
    }


def build_fixture() -> dict[str, Any]:
    """Golden values that matlab/tests compares the MATLAB implementation against."""
    probe_qiskit = {"001": 0.75, "111": 0.25}
    probe_matlab = remap_labels(probe_qiskit, qiskit_to_matlab_label)
    gof_counts = {"00": 520, "11": 480}
    hom_a = {"00": 520, "11": 480}
    hom_b = {"00": 470, "01": 3, "11": 527}
    return {
        "generated_by": "python matlab/tools/compare.py --write-fixture",
        "epsilon": KL_EPSILON,
        "label_cases": [
            {"matlab": "100", "qiskit": "001"},
            {"matlab": "110", "qiskit": "011"},
            {"matlab": "01", "qiskit": "10"},
            {"matlab": "1", "qiskit": "1"},
            {"matlab": "0011", "qiskit": "1100"},
        ],
        "clbit_cases": [
            {
                "matlab": "10",
                "measurements": [{"qubit": 0, "clbit": 1}, {"qubit": 1, "clbit": 0}],
                "num_clbits": 2,
                "qiskit_clbits": "10",
            },
            {
                "matlab": "110",
                "measurements": [{"qubit": 0, "clbit": 0}, {"qubit": 1, "clbit": 1}, {"qubit": 2, "clbit": 2}],
                "num_clbits": 3,
                "qiskit_clbits": "011",
            },
            {
                "matlab": "011",
                "measurements": [{"qubit": 2, "clbit": 0}],
                "num_clbits": 2,
                "qiskit_clbits": "01",
            },
        ],
        "metric_cases": [
            _fixture_case("identical", {"00": 0.5, "11": 0.5}, {"00": 0.5, "11": 0.5}),
            _fixture_case("disjoint", {"0": 1.0}, {"1": 1.0}),
            _fixture_case("shifted", {"00": 0.5, "01": 0.25, "11": 0.25}, {"00": 0.4, "10": 0.1, "11": 0.5}),
            _fixture_case("reversed_unmapped", probe_qiskit, probe_matlab),
            _fixture_case(
                "reversed_mapped",
                probe_qiskit,
                remap_labels(probe_matlab, matlab_to_qiskit_label),
            ),
        ],
        "goodness_of_fit_cases": [
            {
                "counts": gof_counts,
                "expected_probabilities": {"00": 0.5, "11": 0.5},
                "expected": chi_square_goodness_of_fit(gof_counts, {"00": 0.5, "11": 0.5}),
            },
            {
                "counts": {"00": 500, "01": 2, "11": 498},
                "expected_probabilities": {"00": 0.5, "11": 0.5},
                "expected": chi_square_goodness_of_fit({"00": 500, "01": 2, "11": 498}, {"00": 0.5, "11": 0.5}),
            },
        ],
        "homogeneity_cases": [
            {"counts_a": hom_a, "counts_b": hom_b, "expected": chi_square_homogeneity(hom_a, hom_b)},
        ],
        "chi2_sf_cases": [
            {"statistic": x, "dof": k, "p_value": chi2_sf(x, k)}
            for x, k in ((0.0, 1), (1.0, 1), (3.841458820694124, 1), (10.0, 5), (50.0, 7), (2.5, 3))
        ],
    }


def write_fixture(path: Path = FIXTURE_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(build_fixture(), indent=2) + "\n", encoding="utf-8")
    return path


def _summarise_export_dir(directory: Path) -> Iterable[str]:
    """Check each export against itself: Aer counts vs the exact measured distribution."""
    for path in sorted(directory.glob("*.json")):
        if path.name == "manifest.json":
            continue
        export = json.loads(path.read_text(encoding="utf-8"))
        gof = chi_square_goodness_of_fit(export_counts(export), export_measured_exact(export))
        sampled = compare_distributions(export_measured_exact(export), counts_to_probabilities(export_counts(export)))
        yield (
            f"{export['circuit_id']}: Aer vs exact TVD={sampled['total_variation']:.4f} "
            f"chi2 p={gof['p_value']:.4f} {'PASS' if gof['passed'] else 'FAIL'}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--write-fixture", action="store_true", help="Regenerate the MATLAB metric fixture.")
    parser.add_argument("--check-export", type=Path, help="Sanity-check a qiskit_results directory.")
    args = parser.parse_args(argv)
    if args.write_fixture:
        print(write_fixture())
    if args.check_export:
        for line in _summarise_export_dir(args.check_export):
            print(line)
    if not (args.write_fixture or args.check_export):
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
