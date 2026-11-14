"""Tiny training runs: artifacts are written, evaluation reloads them, reruns are identical."""

from __future__ import annotations

import json

import pytest

pytest.importorskip("torch")

from research.config import config_from_dict  # noqa: E402
from research.evaluate import evaluate_run  # noqa: E402
from research.train import run_training  # noqa: E402


def _tiny_config(tmp_path):
    return config_from_dict(
        {
            "name": "test",
            "runs_dir": str(tmp_path / "runs"),
            "dataset": {"seed": 21, "samples_per_class": 15, "path": str(tmp_path / "data" / "tiny.jsonl")},
            "split": {"seed": 21, "train": 0.6, "val": 0.2, "test": 0.2},
            "model": {"hidden_sizes": [16], "dropout": 0.1},
            "train": {"seed": 21, "epochs": 4, "batch_size": 16, "learning_rate": 0.01, "early_stopping_patience": 0},
        }
    )


def test_tiny_training_run_writes_artifacts(tmp_path):
    run_dir = tmp_path / "run"
    result = run_training(_tiny_config(tmp_path), run_dir=run_dir, verbose=False)

    assert result["epochs_run"] == 4
    for name in (
        "checkpoints/best.pt",
        "checkpoints/last.pt",
        "config.json",
        "label_map.json",
        "scaler.json",
        "features.json",
        "metrics.json",
        "history.csv",
        "confusion_matrix_val.csv",
        "confusion_matrix_test.csv",
        "per_class_test.csv",
    ):
        assert (run_dir / name).exists(), name

    metrics = json.loads((run_dir / "metrics.json").read_text())
    for split in ("val", "test"):
        report = metrics[split]
        assert 0.0 <= report["accuracy"] <= 1.0
        assert 0.0 <= report["macro_f1"] <= 1.0
        assert len(report["per_class"]) == 7
        assert sum(map(sum, report["confusion_matrix"])) == report["num_samples"]
    assert metrics["split_sizes"] == {"train": 63, "val": 21, "test": 21}
    assert len((run_dir / "history.csv").read_text().strip().splitlines()) == 5

    evaluation = evaluate_run(run_dir, verbose=False)
    assert evaluation["accuracy"] == metrics["test"]["accuracy"]
    assert evaluation["macro_f1"] == metrics["test"]["macro_f1"]


def test_same_seed_gives_identical_metrics(tmp_path):
    config = _tiny_config(tmp_path)
    first = run_training(config, run_dir=tmp_path / "a", verbose=False)
    second = run_training(config, run_dir=tmp_path / "b", verbose=False)
    assert first["history"] == second["history"]
    assert first["val"] == second["val"]
    assert first["test"] == second["test"]
    assert (tmp_path / "a" / "metrics.json").read_text() == (tmp_path / "b" / "metrics.json").read_text()
