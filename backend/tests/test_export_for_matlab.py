from __future__ import annotations

import json
from pathlib import Path

import pytest
import qiskit
import qiskit_aer

from app.tools import export_for_matlab as exporter

COMMITTED_DIR = Path(__file__).resolve().parents[2] / "matlab" / "data" / "qiskit_results"
SHOTS = 2048
SEED = 7

TOP_LEVEL_KEYS = {
    "schema_version",
    "circuit_id",
    "circuit_name",
    "source",
    "num_qubits",
    "num_clbits",
    "spec",
    "gate_sequence",
    "measurements",
    "bit_ordering",
    "exact",
    "sampled",
    "versions",
    "generated_by",
}
EXACT_KEYS = {
    "method",
    "measurements_removed",
    "bitstrings",
    "probabilities",
    "amplitudes_real",
    "amplitudes_imag",
    "measured_bitstrings",
    "measured_probabilities",
}
SAMPLED_KEYS = {"method", "shots", "seed_simulator", "bitstrings", "counts", "probabilities"}
MANIFEST_KEYS = {"schema_version", "generated_by", "shots", "seed_simulator", "versions", "bit_ordering", "circuits"}


@pytest.fixture(scope="module")
def export_dir(tmp_path_factory) -> Path:
    directory = tmp_path_factory.mktemp("qiskit_results")
    exporter.export_all(directory, shots=SHOTS, seed=SEED)
    return directory


def read(directory: Path, name: str) -> dict:
    return json.loads((directory / f"{name}.json").read_text(encoding="utf-8"))


def nonzero(bitstrings: list[str], probabilities: list[float]) -> dict[str, float]:
    return {b: p for b, p in zip(bitstrings, probabilities) if p > 1e-12}


def test_writes_one_file_per_circuit_and_a_manifest(export_dir: Path) -> None:
    names = sorted(p.name for p in export_dir.glob("*.json"))
    assert names == sorted([f"{c}.json" for c in exporter.CIRCUIT_IDS] + ["manifest.json"])
    manifest = read(export_dir, "manifest")
    assert set(manifest) == MANIFEST_KEYS
    assert [entry["circuit_id"] for entry in manifest["circuits"]] == list(exporter.CIRCUIT_IDS)


def test_cli_writes_files(tmp_path: Path, capsys) -> None:
    code = exporter.main(["--output-dir", str(tmp_path), "--circuits", "bell", "ghz", "--shots", "64"])
    assert code == 0
    assert sorted(p.name for p in tmp_path.glob("*.json")) == ["bell.json", "ghz.json", "manifest.json"]
    assert "bell.json" in capsys.readouterr().out


def test_cli_reports_bad_shots(tmp_path: Path, capsys) -> None:
    assert exporter.main(["--output-dir", str(tmp_path), "--shots", "0"]) == 1
    assert "shots" in capsys.readouterr().err


def test_unknown_circuit_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        exporter.export_all(tmp_path, circuit_ids=["teleport"])


@pytest.mark.parametrize("circuit_id", exporter.CIRCUIT_IDS)
def test_probabilities_sum_to_one(export_dir: Path, circuit_id: str) -> None:
    data = read(export_dir, circuit_id)
    exact = data["exact"]
    assert sum(exact["probabilities"]) == pytest.approx(1.0, abs=1e-12)
    assert sum(exact["measured_probabilities"]) == pytest.approx(1.0, abs=1e-12)
    assert sum(data["sampled"]["probabilities"]) == pytest.approx(1.0, abs=1e-12)
    assert sum(data["sampled"]["counts"]) == SHOTS
    norm = sum(r * r + i * i for r, i in zip(exact["amplitudes_real"], exact["amplitudes_imag"]))
    assert norm == pytest.approx(1.0, abs=1e-12)


@pytest.mark.parametrize(
    ("circuit_id", "expected"),
    [
        ("bell", {"00": 0.5, "11": 0.5}),
        ("ghz", {"000": 0.5, "111": 0.5}),
        ("superposition", {"0": 0.5, "1": 0.5}),
        ("bit_flip", {"1": 1.0}),
        ("bit_order_probe", {"001": 0.75, "111": 0.25}),
    ],
)
def test_reference_probabilities(export_dir: Path, circuit_id: str, expected: dict[str, float]) -> None:
    exact = read(export_dir, circuit_id)["exact"]
    statevector = nonzero(exact["bitstrings"], exact["probabilities"])
    assert statevector == pytest.approx(expected, abs=1e-12)
    measured = nonzero(exact["measured_bitstrings"], exact["measured_probabilities"])
    assert measured == pytest.approx(expected, abs=1e-12)
    assert set(read(export_dir, circuit_id)["sampled"]["bitstrings"]) <= set(expected)


def test_exact_bitstrings_cover_every_basis_state_in_qiskit_order(export_dir: Path) -> None:
    exact = read(export_dir, "ghz")["exact"]
    assert exact["bitstrings"] == [format(i, "03b") for i in range(8)]


def test_gate_coverage_uses_every_supported_gate(export_dir: Path) -> None:
    from app.quantum.gates import SUPPORTED_GATES

    assert set(read(export_dir, "gate_coverage")["gate_sequence"]) == SUPPORTED_GATES


@pytest.mark.parametrize("circuit_id", exporter.CIRCUIT_IDS)
def test_schema_is_stable(export_dir: Path, circuit_id: str) -> None:
    data = read(export_dir, circuit_id)
    assert set(data) == TOP_LEVEL_KEYS
    assert data["schema_version"] == 1
    assert set(data["exact"]) == EXACT_KEYS
    assert set(data["sampled"]) == SAMPLED_KEYS
    assert set(data["versions"]) == {"qiskit", "qiskit_aer", "python"}
    assert data["bit_ordering"]["convention"] == "qiskit_little_endian"
    assert data["gate_sequence"] == [g["gate"] for g in data["spec"]["gates"]]
    assert data["measurements"] == data["spec"]["measurements"]
    assert len(data["exact"]["bitstrings"]) == 2 ** data["num_qubits"]
    assert data["sampled"]["shots"] == SHOTS
    assert data["sampled"]["seed_simulator"] == SEED


def test_reference_specs_come_from_examples(export_dir: Path) -> None:
    from app.quantum.examples import BELL_SPEC, GHZ_SPEC

    assert read(export_dir, "bell")["spec"]["gates"] == BELL_SPEC["gates"]
    assert read(export_dir, "ghz")["spec"]["gates"] == GHZ_SPEC["gates"]
    assert read(export_dir, "bell")["source"] == "reference"
    assert read(export_dir, "gate_coverage")["source"] == "validation"


def test_versions_are_recorded(export_dir: Path) -> None:
    versions = read(export_dir, "bell")["versions"]
    assert versions["qiskit"] == qiskit.__version__
    assert versions["qiskit_aer"] == qiskit_aer.__version__


def test_export_is_deterministic(tmp_path: Path, export_dir: Path) -> None:
    exporter.export_all(tmp_path, shots=SHOTS, seed=SEED)
    for path in export_dir.glob("*.json"):
        assert (tmp_path / path.name).read_text() == path.read_text()


@pytest.mark.skipif(not COMMITTED_DIR.is_dir(), reason="committed MATLAB export is not in this checkout")
@pytest.mark.parametrize("circuit_id", exporter.CIRCUIT_IDS)
def test_committed_export_is_current(tmp_path: Path, circuit_id: str) -> None:
    manifest = json.loads((COMMITTED_DIR / "manifest.json").read_text(encoding="utf-8"))
    committed = read(COMMITTED_DIR, circuit_id)
    exporter.export_all(
        tmp_path,
        circuit_ids=[circuit_id],
        shots=manifest["shots"],
        seed=manifest["seed_simulator"],
    )
    fresh = read(tmp_path, circuit_id)
    for key in ("spec", "gate_sequence", "measurements", "bit_ordering", "sampled"):
        assert committed[key] == fresh[key], key
    assert committed["exact"]["bitstrings"] == fresh["exact"]["bitstrings"]
    assert committed["exact"]["probabilities"] == pytest.approx(fresh["exact"]["probabilities"], abs=1e-12)
    assert committed["versions"]["qiskit"] == fresh["versions"]["qiskit"]
    assert committed["versions"]["qiskit_aer"] == fresh["versions"]["qiskit_aer"]
