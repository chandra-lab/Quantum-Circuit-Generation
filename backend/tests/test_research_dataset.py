"""Synthetic dataset: validity, balance, determinism, and label construction rules."""

from __future__ import annotations

from collections import Counter

import numpy as np
import pytest

from app.schemas.circuit import normalize_spec
from research.config import DatasetConfig, SplitConfig
from research.dataset import CATEGORIES, dataset_digest, generate_dataset, read_dataset, write_dataset
from research.features import extract_features
from research.prep import StandardScaler, stratified_split


@pytest.fixture(scope="module")
def records():
    return generate_dataset(DatasetConfig(seed=11, samples_per_class=40))


def test_every_spec_validates_under_app_limits(records):
    for record in records:
        spec = normalize_spec(record["spec"], max_qubits=8, max_gates=128)
        assert spec.public_dict() == record["spec"]
        assert 1 <= spec.num_qubits <= 8


def test_classes_are_balanced(records):
    counts = Counter(record["category"] for record in records)
    assert set(counts) == set(CATEGORIES)
    assert set(counts.values()) == {40}


def test_same_seed_same_dataset_and_different_seed_differs():
    first = generate_dataset(DatasetConfig(seed=5, samples_per_class=20))
    second = generate_dataset(DatasetConfig(seed=5, samples_per_class=20))
    other = generate_dataset(DatasetConfig(seed=6, samples_per_class=20))
    assert first == second
    assert dataset_digest(first) == dataset_digest(second)
    assert dataset_digest(first) != dataset_digest(other)


def test_write_and_read_round_trip(tmp_path, records):
    path = tmp_path / "data.jsonl"
    meta = write_dataset(records, path, DatasetConfig(seed=11, samples_per_class=40))
    assert read_dataset(path) == records
    assert meta["sha256"] == dataset_digest(records)
    assert path.with_suffix(".meta.json").exists()


def test_labels_follow_construction_rules(records):
    for record in records:
        f = extract_features(normalize_spec(record["spec"], max_qubits=8, max_gates=128))
        category = record["category"]
        if category == "bell":
            assert f["entangling_gates"] == 1 and f["largest_entangling_component"] == 2
            assert f["h_before_cx_control"] == 1 and f["parametric_gates"] == 0
        elif category == "ghz":
            assert f["entangling_gates"] >= 2 and f["largest_entangling_component"] >= 3
            assert f["parametric_gates"] == 0
        elif category in ("superposition", "basis_state", "rotation"):
            assert f["two_qubit_gates"] == 0
        if category == "superposition":
            assert f["count_h"] >= 1 and f["parametric_gates"] == 0
        if category == "basis_state":
            assert f["count_h"] == 0 and f["parametric_gates"] == 0 and f["count_x"] >= 1
        if category == "rotation":
            assert f["parametric_gates"] >= 3
        if category == "swap_permutation":
            assert f["count_swap"] >= 1 and f["entangling_gates"] == 0
        if category == "random_mixed":
            assert f["entangling_gates"] >= 1 and f["parametric_gates"] >= 1


def test_stratified_split_and_train_only_scaler():
    labels = np.repeat(np.arange(7), 20)
    splits = stratified_split(labels, SplitConfig(seed=3, train=0.7, val=0.15, test=0.15))
    all_indices = np.concatenate(list(splits.values()))
    assert sorted(all_indices.tolist()) == list(range(len(labels)))
    for indices in splits.values():
        assert set(Counter(labels[indices].tolist()).values()) == {len(indices) // 7}

    features = np.arange(len(labels) * 2, dtype=np.float64).reshape(-1, 2)
    features[:, 1] = 4.0
    scaler = StandardScaler.fit(features[splits["train"]])
    assert np.allclose(scaler.mean, features[splits["train"]].mean(axis=0))
    assert scaler.scale[1] == 1.0
    assert np.allclose(scaler.transform(features[splits["train"]]).mean(axis=0), 0, atol=1e-6)
