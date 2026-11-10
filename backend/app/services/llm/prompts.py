"""System prompt for natural language to a circuit spec. Never ask for Python."""

from __future__ import annotations

from app.quantum.gates import SUPPORTED_GATES


def system_prompt(max_qubits: int) -> str:
    gates = ", ".join(sorted(SUPPORTED_GATES))
    return (
        "You translate a natural-language quantum computing request into one JSON object "
        "describing a quantum circuit. Return JSON only. Do not return Python, markdown, "
        "or commentary.\n"
        f"Use only these gates: {gates}.\n"
        "rx, ry, and rz require a finite numeric parameter in radians. "
        "Every other gate must set parameter to null.\n"
        f"num_qubits and num_clbits are integers from 1 to {max_qubits}.\n"
        "Qubit and clbit indices are zero-based and must lie inside those sizes.\n"
        "cx and cz list qubits as [control, target] and the two indices must differ.\n"
        "swap qubits must differ.\n"
        "Include at least one measurement. Do not assign two measurements to the same clbit.\n"
        "circuit_name and description are short plain-text strings.\n"
        "Shape: {"
        '"circuit_name": "string", "num_qubits": 1, "num_clbits": 1, '
        '"gates": [{"gate": "h", "qubits": [0], "parameter": null}], '
        '"measurements": [{"qubit": 0, "clbit": 0}], "description": "string"}'
    )


def correction_message(errors: list[str]) -> str:
    joined = "; ".join(errors[:8])
    return (
        "The circuit JSON failed validation: "
        f"{joined}. Return only a corrected JSON object. Do not return Python."
    )
