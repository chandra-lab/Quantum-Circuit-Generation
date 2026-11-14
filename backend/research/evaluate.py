"""Reload a saved run and score a checkpoint.

Without ``--dataset`` the run's own test split is rebuilt from its saved config
(same dataset, same split seed). With ``--dataset`` every sample in that JSONL
file is scored.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import torch

from research.config import load_config
from research.dataset import read_dataset
from research.features import FEATURE_NAMES
from research.metrics import classification_report, write_confusion_csv
from research.model import build_model, seed_everything
from research.prep import StandardScaler, stratified_split
from research.train import load_or_generate_dataset, prepare_arrays


def evaluate_run(
    run_dir: str | Path,
    *,
    checkpoint: str = "best",
    dataset_path: str | Path | None = None,
    verbose: bool = True,
) -> dict[str, Any]:
    run = Path(run_dir)
    config = load_config(run / "config.json")
    seed_everything(config.train.seed, deterministic=config.train.deterministic, num_threads=config.train.num_threads)

    label_map: dict[str, int] = json.loads((run / "label_map.json").read_text(encoding="utf-8"))
    class_names = [name for name, _ in sorted(label_map.items(), key=lambda item: item[1])]
    scaler_state = json.loads((run / "scaler.json").read_text(encoding="utf-8"))
    if scaler_state["feature_names"] != list(FEATURE_NAMES):
        raise ValueError("feature set changed since this run was trained")
    scaler = StandardScaler.from_state_dict(scaler_state)

    if dataset_path is None:
        records, _ = load_or_generate_dataset(config)
        features, labels = prepare_arrays(records, config)
        indices = stratified_split(labels, config.split)["test"]
        features, labels, source = features[indices], labels[indices], "test split"
    else:
        records = read_dataset(dataset_path)
        features, labels = prepare_arrays(records, config)
        source = str(dataset_path)

    model = build_model(torch.load(run / "checkpoints" / f"{checkpoint}.pt", weights_only=True))
    x = torch.from_numpy(scaler.transform(features))
    y = torch.from_numpy(labels)
    with torch.no_grad():
        logits = model(x)
    loss = torch.nn.functional.cross_entropy(logits, y).item()
    report = {
        "source": source,
        "checkpoint": checkpoint,
        "loss": loss,
        **classification_report(labels, np.asarray(logits.argmax(dim=1)), class_names),
    }
    stem = f"evaluation_{checkpoint}"
    (run / f"{stem}.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_confusion_csv(report, run / f"{stem}_confusion_matrix.csv")
    if verbose:
        print(f"{source}: accuracy {report['accuracy']:.4f}, macro F1 {report['macro_f1']:.4f} ({report['num_samples']} samples)")
        print(f"written to {run / (stem + '.json')}")
    return report
