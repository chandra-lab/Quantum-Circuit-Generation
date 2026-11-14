"""Experiment configuration. Every hyperparameter lives here and is saved with each run."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, fields, is_dataclass
from pathlib import Path
from typing import Any

RESEARCH_DIR = Path(__file__).resolve().parent
BACKEND_DIR = RESEARCH_DIR.parent
DEFAULT_CONFIG_PATH = RESEARCH_DIR / "configs" / "default.json"


def resolve_path(path: str | Path) -> Path:
    """Relative paths in configs are relative to backend/, whatever the working directory."""
    candidate = Path(path)
    return candidate if candidate.is_absolute() else BACKEND_DIR / candidate


@dataclass
class DatasetConfig:
    seed: int = 1234
    samples_per_class: int = 300
    min_qubits: int = 1
    # Matches the app's MAX_QUBITS default. Specs are validated against this bound.
    max_qubits: int = 8
    max_gates: int = 128
    max_padding_gates: int = 4
    path: str = "research/data/circuits.jsonl"


@dataclass
class SplitConfig:
    seed: int = 1234
    train: float = 0.7
    val: float = 0.15
    test: float = 0.15


@dataclass
class ModelConfig:
    hidden_sizes: list[int] = field(default_factory=lambda: [64, 64])
    dropout: float = 0.1


@dataclass
class TrainConfig:
    seed: int = 1234
    epochs: int = 60
    batch_size: int = 64
    learning_rate: float = 1e-3
    weight_decay: float = 1e-4
    early_stopping_patience: int = 10
    monitor: str = "val_macro_f1"
    device: str = "cpu"
    deterministic: bool = True
    num_threads: int = 1


@dataclass
class ExperimentConfig:
    name: str = "default"
    runs_dir: str = "research/runs"
    dataset: DatasetConfig = field(default_factory=DatasetConfig)
    split: SplitConfig = field(default_factory=SplitConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    train: TrainConfig = field(default_factory=TrainConfig)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _build(cls: type, values: dict[str, Any]) -> Any:
    known = {f.name: f for f in fields(cls)}
    unknown = set(values) - set(known)
    if unknown:
        raise ValueError(f"unknown {cls.__name__} keys: {sorted(unknown)}")
    kwargs: dict[str, Any] = {}
    for name, value in values.items():
        default = known[name].default_factory() if callable(known[name].default_factory) else None
        if is_dataclass(default) and isinstance(value, dict):
            kwargs[name] = _build(type(default), value)
        else:
            kwargs[name] = value
    return cls(**kwargs)


def config_from_dict(values: dict[str, Any]) -> ExperimentConfig:
    config = _build(ExperimentConfig, values)
    validate_config(config)
    return config


def load_config(path: str | Path | None = None) -> ExperimentConfig:
    source = Path(path) if path else DEFAULT_CONFIG_PATH
    with source.open(encoding="utf-8") as handle:
        return config_from_dict(json.load(handle))


def save_config(config: ExperimentConfig, path: str | Path) -> None:
    Path(path).write_text(json.dumps(config.to_dict(), indent=2) + "\n", encoding="utf-8")


def validate_config(config: ExperimentConfig) -> None:
    data = config.dataset
    if not 1 <= data.min_qubits <= data.max_qubits <= 16:
        raise ValueError("dataset qubit bounds must satisfy 1 <= min_qubits <= max_qubits <= 16")
    if data.max_qubits < 3:
        raise ValueError("dataset.max_qubits must be at least 3 so GHZ samples exist")
    if data.samples_per_class < 3:
        raise ValueError("dataset.samples_per_class must be at least 3")
    split = config.split
    if min(split.train, split.val, split.test) <= 0 or abs(split.train + split.val + split.test - 1) > 1e-9:
        raise ValueError("split fractions must be positive and sum to 1")
    if config.train.monitor not in {"val_macro_f1", "val_accuracy", "val_loss"}:
        raise ValueError("train.monitor must be val_macro_f1, val_accuracy or val_loss")
    if config.train.device != "cpu":
        raise ValueError("only the cpu device is supported")
