"""Stratified splits and a standard scaler fitted on the training split only."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from research.config import SplitConfig


def stratified_split(labels: np.ndarray, config: SplitConfig) -> dict[str, np.ndarray]:
    """Split indices per class with a seeded permutation, so every split keeps class ratios."""
    rng = np.random.default_rng(config.seed)
    parts: dict[str, list[np.ndarray]] = {"train": [], "val": [], "test": []}
    for label in np.unique(labels):
        indices = rng.permutation(np.flatnonzero(labels == label))
        n_val = max(1, round(len(indices) * config.val))
        n_test = max(1, round(len(indices) * config.test))
        n_train = len(indices) - n_val - n_test
        if n_train < 1:
            raise ValueError(f"class {label} has too few samples to split")
        parts["train"].append(indices[:n_train])
        parts["val"].append(indices[n_train : n_train + n_val])
        parts["test"].append(indices[n_train + n_val :])
    return {name: np.sort(np.concatenate(chunks)) for name, chunks in parts.items()}


@dataclass
class StandardScaler:
    mean: np.ndarray
    scale: np.ndarray

    @classmethod
    def fit(cls, features: np.ndarray) -> StandardScaler:
        mean = features.mean(axis=0)
        std = features.std(axis=0)
        # Constant columns (e.g. a gate never used in train) keep scale 1 instead of dividing by 0.
        return cls(mean=mean, scale=np.where(std > 0, std, 1.0))

    def transform(self, features: np.ndarray) -> np.ndarray:
        return ((features - self.mean) / self.scale).astype(np.float32)

    def state_dict(self, feature_names: list[str]) -> dict[str, Any]:
        return {
            "type": "standard",
            "fitted_on": "train",
            "feature_names": feature_names,
            "mean": self.mean.tolist(),
            "scale": self.scale.tolist(),
        }

    @classmethod
    def from_state_dict(cls, state: dict[str, Any]) -> StandardScaler:
        return cls(mean=np.asarray(state["mean"], dtype=np.float64), scale=np.asarray(state["scale"], dtype=np.float64))
