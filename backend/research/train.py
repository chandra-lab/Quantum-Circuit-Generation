"""Train the circuit-category classifier and write a self-contained run directory.

Usage: ``python -m research.train --config research/configs/default.json``
(the same as ``python -m research train ...``).
"""

from __future__ import annotations

import csv
import json
import sys
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import torch
from torch import nn

from research.config import ExperimentConfig, resolve_path, save_config
from research.dataset import CATEGORIES, generate_dataset, read_dataset, write_dataset
from research.features import FEATURE_DESCRIPTIONS, FEATURE_NAMES, feature_matrix
from research.metrics import classification_report, write_confusion_csv, write_per_class_csv
from research.model import CircuitClassifier, seed_everything
from research.prep import StandardScaler, stratified_split


def load_or_generate_dataset(config: ExperimentConfig) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Reuse the dataset file only when its metadata says it was built from this exact config."""
    path = resolve_path(config.dataset.path)
    meta_path = path.with_suffix(".meta.json")
    if path.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("config") == asdict(config.dataset):
            return read_dataset(path), meta
    records = generate_dataset(config.dataset)
    return records, write_dataset(records, path, config.dataset)


def prepare_arrays(records: list[dict[str, Any]], config: ExperimentConfig) -> tuple[np.ndarray, np.ndarray]:
    label_map = {name: index for index, name in enumerate(CATEGORIES)}
    features = np.asarray(
        feature_matrix(
            [r["spec"] for r in records],
            max_qubits=config.dataset.max_qubits,
            max_gates=config.dataset.max_gates,
        ),
        dtype=np.float64,
    )
    labels = np.asarray([label_map[r["category"]] for r in records], dtype=np.int64)
    return features, labels


@torch.no_grad()
def predict(model: nn.Module, features: torch.Tensor, labels: torch.Tensor) -> tuple[float, np.ndarray]:
    model.eval()
    logits = model(features)
    loss = nn.functional.cross_entropy(logits, labels).item()
    return loss, logits.argmax(dim=1).numpy()


def _monitor_value(name: str, loss: float, report: dict[str, Any]) -> float:
    if name == "val_loss":
        return -loss
    return report["accuracy"] if name == "val_accuracy" else report["macro_f1"]


def _checkpoint(model: nn.Module, config: ExperimentConfig, input_dim: int, epoch: int, value: float) -> dict[str, Any]:
    return {
        "model_state": model.state_dict(),
        "epoch": epoch,
        "input_dim": input_dim,
        "num_classes": len(CATEGORIES),
        "hidden_sizes": list(config.model.hidden_sizes),
        "dropout": config.model.dropout,
        "monitor": config.train.monitor,
        "monitor_value": value,
    }


def _write_loss_plot(history: list[dict[str, Any]], path: Path) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    epochs = [row["epoch"] for row in history]
    figure, axis = plt.subplots(figsize=(6, 4))
    axis.plot(epochs, [row["train_loss"] for row in history], label="train loss")
    axis.plot(epochs, [row["val_loss"] for row in history], label="validation loss")
    axis.set_xlabel("epoch")
    axis.set_ylabel("cross-entropy")
    axis.legend()
    figure.tight_layout()
    figure.savefig(path, dpi=120)
    plt.close(figure)


def default_run_dir(config: ExperimentConfig) -> Path:
    stamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    return resolve_path(config.runs_dir) / f"{config.name}-{stamp}"


def run_training(config: ExperimentConfig, run_dir: str | Path | None = None, *, verbose: bool = True) -> dict[str, Any]:
    train_cfg = config.train
    seed_everything(train_cfg.seed, deterministic=train_cfg.deterministic, num_threads=train_cfg.num_threads)

    target = Path(run_dir) if run_dir else default_run_dir(config)
    (target / "checkpoints").mkdir(parents=True, exist_ok=True)

    records, dataset_meta = load_or_generate_dataset(config)
    features, labels = prepare_arrays(records, config)
    splits = stratified_split(labels, config.split)
    scaler = StandardScaler.fit(features[splits["train"]])

    tensors = {
        name: (torch.from_numpy(scaler.transform(features[idx])), torch.from_numpy(labels[idx]))
        for name, idx in splits.items()
    }
    x_train, y_train = tensors["train"]
    x_val, y_val = tensors["val"]

    model = CircuitClassifier(features.shape[1], len(CATEGORIES), config.model.hidden_sizes, config.model.dropout)
    optimizer = torch.optim.Adam(model.parameters(), lr=train_cfg.learning_rate, weight_decay=train_cfg.weight_decay)
    loss_fn = nn.CrossEntropyLoss()
    batch_generator = torch.Generator().manual_seed(train_cfg.seed)

    history: list[dict[str, Any]] = []
    best_value = -float("inf")
    best_loss = float("inf")
    best_epoch = 0
    stale = 0
    for epoch in range(1, train_cfg.epochs + 1):
        model.train()
        order = torch.randperm(len(x_train), generator=batch_generator)
        running = 0.0
        for start in range(0, len(order), train_cfg.batch_size):
            batch = order[start : start + train_cfg.batch_size]
            optimizer.zero_grad()
            loss = loss_fn(model(x_train[batch]), y_train[batch])
            loss.backward()
            optimizer.step()
            running += loss.item() * len(batch)

        val_loss, val_pred = predict(model, x_val, y_val)
        val_report = classification_report(y_val.numpy(), val_pred, list(CATEGORIES))
        row = {
            "epoch": epoch,
            "train_loss": running / len(x_train),
            "val_loss": val_loss,
            "val_accuracy": val_report["accuracy"],
            "val_macro_f1": val_report["macro_f1"],
        }
        history.append(row)
        value = _monitor_value(train_cfg.monitor, val_loss, val_report)
        # Accuracy and F1 plateau at small validation sizes, so ties go to the lower validation loss.
        improved = value > best_value or (value == best_value and val_loss < best_loss)
        if improved:
            best_value, best_loss, best_epoch, stale = value, val_loss, epoch, 0
            torch.save(_checkpoint(model, config, features.shape[1], epoch, value), target / "checkpoints" / "best.pt")
        else:
            stale += 1
        if verbose:
            print(
                f"epoch {epoch:3d}  train_loss {row['train_loss']:.4f}  val_loss {val_loss:.4f}  "
                f"val_acc {row['val_accuracy']:.4f}  val_macro_f1 {row['val_macro_f1']:.4f}"
                + ("  *" if improved else "")
            )
        if train_cfg.early_stopping_patience > 0 and stale >= train_cfg.early_stopping_patience:
            break

    torch.save(_checkpoint(model, config, features.shape[1], len(history), value), target / "checkpoints" / "last.pt")

    best = torch.load(target / "checkpoints" / "best.pt", weights_only=True)
    model.load_state_dict(best["model_state"])
    reports = {}
    for name in ("val", "test"):
        x, y = tensors[name]
        loss, pred = predict(model, x, y)
        reports[name] = {"loss": loss, **classification_report(y.numpy(), pred, list(CATEGORIES))}
        write_confusion_csv(reports[name], target / f"confusion_matrix_{name}.csv")
        write_per_class_csv(reports[name], target / f"per_class_{name}.csv")

    metrics = {
        "description": "Circuit-category classifier on synthetic, rule-labelled specs. Single run.",
        "checkpoint": "best",
        "best_epoch": best_epoch,
        "epochs_run": len(history),
        "monitor": train_cfg.monitor,
        "split_sizes": {name: int(len(idx)) for name, idx in splits.items()},
        "dataset": {key: dataset_meta[key] for key in ("num_samples", "class_counts", "sha256")},
        "torch_version": torch.__version__,
        "val": reports["val"],
        "test": reports["test"],
    }

    save_config(config, target / "config.json")
    (target / "label_map.json").write_text(
        json.dumps({name: index for index, name in enumerate(CATEGORIES)}, indent=2) + "\n", encoding="utf-8"
    )
    (target / "scaler.json").write_text(json.dumps(scaler.state_dict(list(FEATURE_NAMES)), indent=2) + "\n", encoding="utf-8")
    (target / "features.json").write_text(json.dumps(FEATURE_DESCRIPTIONS, indent=2) + "\n", encoding="utf-8")
    (target / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    with (target / "history.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(history[0]))
        writer.writeheader()
        writer.writerows(history)
    _write_loss_plot(history, target / "loss_curve.png")

    if verbose:
        print(
            f"best epoch {best_epoch}: test accuracy {reports['test']['accuracy']:.4f}, "
            f"test macro F1 {reports['test']['macro_f1']:.4f}"
        )
        print(f"run written to {target}")
    return {"run_dir": str(target), "history": history, **metrics}


def main(argv: list[str] | None = None) -> int:
    from research.cli import main as cli_main

    return cli_main(["train", *(argv if argv is not None else sys.argv[1:])])


if __name__ == "__main__":
    raise SystemExit(main())
