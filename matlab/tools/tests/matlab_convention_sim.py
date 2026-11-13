"""Tiny statevector simulator that reports results the way MATLAB's quantumState does.

Test double only. Qubits are 1-based, qubit 1 is the leftmost character of a basis
label, and amplitudes are ordered like quantumState.BasisStates ("00", "01", "10", "11").
It lets pytest exercise the Qiskit <-> MATLAB mapping on real exports without MATLAB.
"""

from __future__ import annotations

import cmath
import math
from collections.abc import Mapping, Sequence
from typing import Any

Matrix = tuple[tuple[complex, complex], tuple[complex, complex]]

_S2 = 1 / math.sqrt(2)


def _single(name: str, theta: float | None) -> Matrix:
    if name == "i":
        return ((1, 0), (0, 1))
    if name == "x":
        return ((0, 1), (1, 0))
    if name == "y":
        return ((0, -1j), (1j, 0))
    if name == "z":
        return ((1, 0), (0, -1))
    if name == "h":
        return ((_S2, _S2), (_S2, -_S2))
    if name == "s":
        return ((1, 0), (0, 1j))
    if name == "t":
        return ((1, 0), (0, cmath.exp(1j * math.pi / 4)))
    assert theta is not None
    c, s = math.cos(theta / 2), math.sin(theta / 2)
    if name == "rx":
        return ((c, -1j * s), (-1j * s, c))
    if name == "ry":
        return ((c, -s), (s, c))
    if name == "rz":
        return ((cmath.exp(-1j * theta / 2), 0), (0, cmath.exp(1j * theta / 2)))
    raise ValueError(f"unsupported gate {name!r}")


def _bit(index: int, qubit: int, n: int) -> int:
    return (index >> (n - qubit)) & 1


def _flip(index: int, qubit: int, n: int) -> int:
    return index ^ (1 << (n - qubit))


def simulate(num_qubits: int, gates: Sequence[tuple[str, Sequence[int], float | None]]) -> list[complex]:
    """``gates`` are (name, 1-based qubits, angle). Returns MATLAB-ordered amplitudes."""
    n = num_qubits
    state = [0j] * (2**n)
    state[0] = 1
    for name, qubits, theta in gates:
        new = list(state)
        if name in ("cx", "cz"):
            control, target = qubits
            for i, amp in enumerate(state):
                if not _bit(i, control, n):
                    continue
                if name == "cx":
                    new[_flip(i, target, n)] = amp
                elif _bit(i, target, n):
                    new[i] = -amp
        elif name == "swap":
            a, b = qubits
            for i, amp in enumerate(state):
                j = i
                if _bit(i, a, n) != _bit(i, b, n):
                    j = _flip(_flip(i, a, n), b, n)
                new[j] = amp
        else:
            (q,) = qubits
            m = _single(name, theta)
            new = [0j] * len(state)
            for i, amp in enumerate(state):
                bit = _bit(i, q, n)
                partner = _flip(i, q, n)
                new[i] += m[bit][bit] * amp
                new[partner] += m[1 - bit][bit] * amp
        state = new
    return state


def basis_states(num_qubits: int) -> list[str]:
    return [format(i, f"0{num_qubits}b") for i in range(2**num_qubits)]


def simulate_spec(spec: Mapping[str, Any]) -> dict[str, float]:
    """Run an exported (0-based) spec with 1-based MATLAB indices. Returns MATLAB label -> probability."""
    gates = [
        (g["gate"], [q + 1 for q in g["qubits"]], g.get("parameter"))
        for g in spec["gates"]
    ]
    amplitudes = simulate(spec["num_qubits"], gates)
    return {label: abs(a) ** 2 for label, a in zip(basis_states(spec["num_qubits"]), amplitudes)}
