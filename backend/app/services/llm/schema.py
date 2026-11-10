"""JSON schema sent to Groq structured output."""

from __future__ import annotations

from app.quantum.gates import SUPPORTED_GATES


def circuit_json_schema() -> dict[str, object]:
    gate_names = sorted(SUPPORTED_GATES)
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "circuit_name": {"type": "string"},
            "num_qubits": {"type": "integer"},
            "num_clbits": {"type": "integer"},
            "description": {"type": "string"},
            "gates": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "gate": {"type": "string", "enum": gate_names},
                        "qubits": {
                            "type": "array",
                            "items": {"type": "integer"},
                        },
                        "parameter": {"type": ["number", "null"]},
                    },
                    "required": ["gate", "qubits", "parameter"],
                },
            },
            "measurements": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "qubit": {"type": "integer"},
                        "clbit": {"type": "integer"},
                    },
                    "required": ["qubit", "clbit"],
                },
            },
        },
        "required": [
            "circuit_name",
            "num_qubits",
            "num_clbits",
            "gates",
            "measurements",
            "description",
        ],
    }


def response_format(*, strict: bool) -> dict[str, object]:
    if not strict:
        return {"type": "json_object"}
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "quantum_circuit_spec",
            "description": "A quantum circuit specification using the supported gate set.",
            "strict": True,
            "schema": circuit_json_schema(),
        },
    }
