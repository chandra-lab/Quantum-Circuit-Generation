"""MLP classifier over circuit features, plus seeding helpers. Imports torch."""

from __future__ import annotations

import os
import random

import numpy as np
import torch
from torch import nn


def seed_everything(seed: int, *, deterministic: bool = True, num_threads: int = 1) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(num_threads)
    if deterministic:
        # Only consulted by CUDA kernels, but harmless on CPU and keeps the setting explicit.
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
        torch.use_deterministic_algorithms(True)


class CircuitClassifier(nn.Module):
    def __init__(self, input_dim: int, num_classes: int, hidden_sizes: list[int], dropout: float) -> None:
        super().__init__()
        layers: list[nn.Module] = []
        width = input_dim
        for hidden in hidden_sizes:
            layers += [nn.Linear(width, hidden), nn.ReLU(), nn.Dropout(dropout)]
            width = hidden
        layers.append(nn.Linear(width, num_classes))
        self.network = nn.Sequential(*layers)

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return self.network(features)


def build_model(checkpoint: dict) -> CircuitClassifier:
    model = CircuitClassifier(
        input_dim=checkpoint["input_dim"],
        num_classes=checkpoint["num_classes"],
        hidden_sizes=list(checkpoint["hidden_sizes"]),
        dropout=checkpoint["dropout"],
    )
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    return model
