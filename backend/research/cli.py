"""Command line entry point: ``python -m research {generate-dataset,train,evaluate}``.

Run from ``backend/`` (or ``/app`` in the image) so ``app`` and ``research`` import.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from research.config import DEFAULT_CONFIG_PATH, load_config, resolve_path


def _apply_overrides(config, args: argparse.Namespace):
    if getattr(args, "seed", None) is not None:
        config.dataset.seed = config.split.seed = config.train.seed = args.seed
    if getattr(args, "samples_per_class", None) is not None:
        config.dataset.samples_per_class = args.samples_per_class
    if getattr(args, "dataset", None):
        config.dataset.path = args.dataset
    if getattr(args, "epochs", None) is not None:
        config.train.epochs = args.epochs
    if getattr(args, "runs_dir", None):
        config.runs_dir = args.runs_dir
    if getattr(args, "name", None):
        config.name = args.name
    return config


def _cmd_generate(args: argparse.Namespace) -> int:
    from research.dataset import generate_dataset, write_dataset

    config = _apply_overrides(load_config(args.config), args)
    records = generate_dataset(config.dataset)
    meta = write_dataset(records, resolve_path(config.dataset.path), config.dataset)
    print(f"wrote {meta['num_samples']} specs to {meta['path']}")
    print(f"class counts: {meta['class_counts']}")
    print(f"sha256: {meta['sha256']}")
    return 0


def _cmd_train(args: argparse.Namespace) -> int:
    from research.train import run_training

    config = _apply_overrides(load_config(args.config), args)
    run_training(config, run_dir=resolve_path(args.run_dir) if args.run_dir else None)
    return 0


def _cmd_evaluate(args: argparse.Namespace) -> int:
    from research.evaluate import evaluate_run

    evaluate_run(
        resolve_path(args.run_dir),
        checkpoint=args.checkpoint,
        dataset_path=resolve_path(args.dataset) if args.dataset else None,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m research",
        description="Circuit-category classifier on synthetic, rule-labelled circuit specs.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def add_config(p: argparse.ArgumentParser) -> None:
        p.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help="JSON experiment config")
        p.add_argument("--seed", type=int, help="override dataset, split and training seeds")
        p.add_argument("--samples-per-class", type=int)
        p.add_argument("--dataset", help="dataset JSONL path (relative paths are under backend/)")

    gen = sub.add_parser("generate-dataset", help="write the synthetic dataset as JSONL")
    add_config(gen)
    gen.set_defaults(func=_cmd_generate)

    train = sub.add_parser("train", help="train, validate every epoch, test the best checkpoint")
    add_config(train)
    train.add_argument("--epochs", type=int)
    train.add_argument("--name", help="run name prefix")
    train.add_argument("--runs-dir", help="parent directory for runs")
    train.add_argument("--run-dir", help="exact run directory (overrides --runs-dir and --name)")
    train.set_defaults(func=_cmd_train)

    evaluate = sub.add_parser("evaluate", help="score a saved checkpoint")
    evaluate.add_argument("--run-dir", required=True)
    evaluate.add_argument("--checkpoint", choices=("best", "last"), default="best")
    evaluate.add_argument("--dataset", help="score every sample in this JSONL instead of the run's test split")
    evaluate.set_defaults(func=_cmd_evaluate)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
