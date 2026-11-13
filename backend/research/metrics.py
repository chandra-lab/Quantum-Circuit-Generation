"""Classification metrics in NumPy, so no scikit-learn dependency is needed."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np


def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, num_classes: int) -> np.ndarray:
    """Rows are true classes, columns are predicted classes."""
    matrix = np.zeros((num_classes, num_classes), dtype=np.int64)
    np.add.at(matrix, (y_true, y_pred), 1)
    return matrix


def classification_report(
    y_true: np.ndarray, y_pred: np.ndarray, class_names: list[str]
) -> dict[str, Any]:
    matrix = confusion_matrix(y_true, y_pred, len(class_names))
    true_positive = np.diag(matrix).astype(np.float64)
    predicted = matrix.sum(axis=0).astype(np.float64)
    support = matrix.sum(axis=1).astype(np.float64)
    # A class with no predictions (or no support) scores 0, matching scikit-learn's zero_division=0.
    precision = np.divide(true_positive, predicted, out=np.zeros_like(true_positive), where=predicted > 0)
    recall = np.divide(true_positive, support, out=np.zeros_like(true_positive), where=support > 0)
    denom = precision + recall
    f1 = np.divide(2 * precision * recall, denom, out=np.zeros_like(denom), where=denom > 0)
    per_class = {
        name: {
            "precision": float(precision[i]),
            "recall": float(recall[i]),
            "f1": float(f1[i]),
            "support": int(support[i]),
        }
        for i, name in enumerate(class_names)
    }
    return {
        "num_samples": int(len(y_true)),
        "accuracy": float(true_positive.sum() / max(len(y_true), 1)),
        "macro_precision": float(precision.mean()),
        "macro_recall": float(recall.mean()),
        "macro_f1": float(f1.mean()),
        "per_class": per_class,
        "confusion_matrix": matrix.tolist(),
        "class_names": list(class_names),
    }


def write_confusion_csv(report: dict[str, Any], path: Path) -> None:
    names = report["class_names"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["true\\pred", *names])
        for name, row in zip(names, report["confusion_matrix"]):
            writer.writerow([name, *row])


def write_per_class_csv(report: dict[str, Any], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["class", "precision", "recall", "f1", "support"])
        for name, row in report["per_class"].items():
            writer.writerow([name, f"{row['precision']:.6f}", f"{row['recall']:.6f}", f"{row['f1']:.6f}", row["support"]])
