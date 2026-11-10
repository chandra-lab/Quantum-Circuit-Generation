"""Allowlist of gates the builder may apply. Nothing outside this set is callable."""

SINGLE_QUBIT_GATES = frozenset({"i", "x", "y", "z", "h", "s", "t"})
PARAMETRIC_GATES = frozenset({"rx", "ry", "rz"})
TWO_QUBIT_GATES = frozenset({"cx", "cz", "swap"})
SUPPORTED_GATES = frozenset(SINGLE_QUBIT_GATES | PARAMETRIC_GATES | TWO_QUBIT_GATES)


def gate_arity(name: str) -> int:
    if name in TWO_QUBIT_GATES:
        return 2
    return 1


def gate_takes_parameter(name: str) -> bool:
    return name in PARAMETRIC_GATES
