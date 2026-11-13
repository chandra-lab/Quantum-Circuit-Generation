"""Deterministic synthetic dataset of rule-labelled circuit specs.

Each category has a generator that builds a spec with a fixed structural recipe,
then randomises qubit count, qubit choice, gate order where it does not matter,
angles, and harmless padding. The label is the recipe that built the spec, so it
is correct by construction. Every spec passes the app's ``normalize_spec``.

Padding never changes the prepared state: it inserts identity gates anywhere,
or an adjacent self-inverse pair (``x x`` or ``z z``) on one qubit.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from collections import Counter
from collections.abc import Callable, Iterable
from dataclasses import asdict
from pathlib import Path
from typing import Any

from app.schemas.circuit import normalize_spec
from research.config import DatasetConfig

CATEGORIES: tuple[str, ...] = (
    "superposition",
    "bell",
    "ghz",
    "basis_state",
    "rotation",
    "swap_permutation",
    "random_mixed",
)

CATEGORY_DESCRIPTIONS: dict[str, str] = {
    "superposition": "H on a non-empty subset of qubits, optionally followed by a phase gate (z, s, t) on one of them. No two-qubit gates.",
    "bell": "One Bell pair: H on a control, one CX to a target, with optional X on the target before and Z on the control after (the four Bell states).",
    "ghz": "H on a root, then CX gates fanning out (star) or chaining (line) across 3 or more qubits.",
    "basis_state": "X on a non-empty subset of qubits (a computational basis state), optionally one Z. No H, rotations or two-qubit gates.",
    "rotation": "3 to 12 rx/ry/rz gates with |angle| >= 0.1 on random qubits, at most one extra h/s/t. No two-qubit gates.",
    "swap_permutation": "X on a non-empty subset, then 1 to 4 SWAP gates permuting the basis state. No CX/CZ.",
    "random_mixed": "6 to 16 gates drawn from the full allowlist, guaranteed to contain a CX or CZ, a rotation, and one of h/y/s/t.",
}

ROTATIONS = ("rx", "ry", "rz")
NON_ROTATION_SINGLE = ("x", "y", "z", "h", "s", "t")
MIXED_POOL = ("x", "y", "z", "h", "s", "t", "rx", "ry", "rz", "cx", "cz", "swap")

Gate = dict[str, Any]


def _g(name: str, *qubits: int, parameter: float | None = None) -> Gate:
    gate: Gate = {"gate": name, "qubits": list(qubits)}
    if parameter is not None:
        gate["parameter"] = parameter
    return gate


def _angle(rng: random.Random) -> float:
    magnitude = rng.uniform(0.1, math.pi)
    return round(magnitude if rng.random() < 0.5 else -magnitude, 4)


def _subset(rng: random.Random, n: int, minimum: int = 1) -> list[int]:
    size = rng.randint(minimum, n)
    return rng.sample(range(n), size)


def _gen_superposition(rng: random.Random, n: int) -> list[Gate]:
    targets = _subset(rng, n)
    gates = [_g("h", q) for q in targets]
    if rng.random() < 0.3:
        gates.append(_g(rng.choice(("z", "s", "t")), rng.choice(targets)))
    return gates


def _gen_bell(rng: random.Random, n: int) -> list[Gate]:
    control, target = rng.sample(range(n), 2)
    gates: list[Gate] = []
    if rng.random() < 0.5:
        gates.append(_g("x", target))
    gates += [_g("h", control), _g("cx", control, target)]
    if rng.random() < 0.5:
        gates.append(_g("z", control))
    return gates


def _gen_ghz(rng: random.Random, n: int) -> list[Gate]:
    chosen = rng.sample(range(n), rng.randint(3, n))
    root = chosen[0]
    gates = [_g("h", root)]
    if rng.random() < 0.5:
        gates += [_g("cx", root, q) for q in chosen[1:]]
    else:
        gates += [_g("cx", a, b) for a, b in zip(chosen, chosen[1:])]
    return gates


def _gen_basis_state(rng: random.Random, n: int) -> list[Gate]:
    gates = [_g("x", q) for q in _subset(rng, n)]
    if rng.random() < 0.3:
        gates.append(_g("z", rng.randrange(n)))
    return gates


def _gen_rotation(rng: random.Random, n: int) -> list[Gate]:
    gates = [
        _g(rng.choice(ROTATIONS), rng.randrange(n), parameter=_angle(rng))
        for _ in range(rng.randint(3, 12))
    ]
    if len(gates) >= 4 and rng.random() < 0.3:
        gates.insert(rng.randrange(len(gates) + 1), _g(rng.choice(("h", "s", "t")), rng.randrange(n)))
    return gates


def _gen_swap_permutation(rng: random.Random, n: int) -> list[Gate]:
    gates = [_g("x", q) for q in _subset(rng, n)]
    gates += [_g("swap", *rng.sample(range(n), 2)) for _ in range(rng.randint(1, 4))]
    return gates


def _random_gate(rng: random.Random, name: str, n: int) -> Gate:
    if name in ("cx", "cz", "swap"):
        return _g(name, *rng.sample(range(n), 2))
    if name in ROTATIONS:
        return _g(name, rng.randrange(n), parameter=_angle(rng))
    return _g(name, rng.randrange(n))


def _gen_random_mixed(rng: random.Random, n: int) -> list[Gate]:
    names = [rng.choice(("cx", "cz")), rng.choice(ROTATIONS), rng.choice(("h", "y", "s", "t"))]
    names += [rng.choice(MIXED_POOL) for _ in range(rng.randint(6, 16) - len(names))]
    rng.shuffle(names)
    return [_random_gate(rng, name, n) for name in names]


GENERATORS: dict[str, tuple[int, Callable[[random.Random, int], list[Gate]]]] = {
    "superposition": (1, _gen_superposition),
    "bell": (2, _gen_bell),
    "ghz": (3, _gen_ghz),
    "basis_state": (1, _gen_basis_state),
    "rotation": (1, _gen_rotation),
    "swap_permutation": (2, _gen_swap_permutation),
    "random_mixed": (2, _gen_random_mixed),
}


def _pad(rng: random.Random, gates: list[Gate], n: int, max_padding: int) -> list[Gate]:
    padded = list(gates)
    for _ in range(rng.randint(0, max_padding)):
        qubit = rng.randrange(n)
        position = rng.randint(0, len(padded))
        if rng.random() < 0.6:
            padded.insert(position, _g("i", qubit))
        else:
            name = rng.choice(("x", "z"))
            padded[position:position] = [_g(name, qubit), _g(name, qubit)]
    return padded


def make_spec(category: str, index: int, rng: random.Random, config: DatasetConfig) -> dict[str, Any]:
    category_min, generator = GENERATORS[category]
    low = max(category_min, config.min_qubits)
    n = rng.randint(low, config.max_qubits)
    gates = _pad(rng, generator(rng, n), n, config.max_padding_gates)
    payload = {
        "circuit_name": f"synthetic-{index:05d}",
        "num_qubits": n,
        "num_clbits": n,
        "gates": gates,
        "measurements": [{"qubit": q, "clbit": q} for q in range(n)],
        "description": "Synthetic rule-labelled sample for the research classifier.",
    }
    return normalize_spec(payload, max_qubits=config.max_qubits, max_gates=config.max_gates).public_dict()


def generate_dataset(config: DatasetConfig) -> list[dict[str, Any]]:
    """Return ``samples_per_class`` records per category, shuffled with ``config.seed``."""
    rng = random.Random(config.seed)
    plan = [category for category in CATEGORIES for _ in range(config.samples_per_class)]
    rng.shuffle(plan)
    return [
        {"id": index, "category": category, "spec": make_spec(category, index, rng, config)}
        for index, category in enumerate(plan)
    ]


def dataset_digest(records: Iterable[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(json.dumps(record, sort_keys=True).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def write_dataset(records: list[dict[str, Any]], path: str | Path, config: DatasetConfig) -> dict[str, Any]:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    meta = {
        "path": str(target),
        "num_samples": len(records),
        "class_counts": dict(sorted(Counter(r["category"] for r in records).items())),
        "sha256": dataset_digest(records),
        "categories": CATEGORY_DESCRIPTIONS,
        "config": asdict(config),
    }
    target.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    return meta


def read_dataset(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]
