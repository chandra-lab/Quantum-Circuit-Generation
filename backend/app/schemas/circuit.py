"""Circuit spec schema. Gate names are canonicalized to the allowlist."""

from __future__ import annotations

import math
from typing import Any

from pydantic import ConfigDict, Field, StrictInt, ValidationError, field_validator, model_validator
from pydantic import BaseModel

from app.core.errors import CircuitValidationError
from app.quantum.gates import SUPPORTED_GATES, gate_arity, gate_takes_parameter


class GateSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gate: str
    qubits: list[StrictInt] = Field(min_length=1, max_length=2)
    parameter: float | None = None

    @field_validator("gate", mode="before")
    @classmethod
    def canonicalize_gate(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("gate must be a string")
        name = value.strip().lower()
        if name not in SUPPORTED_GATES:
            raise ValueError(f"unsupported gate '{value}'")
        return name

    @field_validator("parameter", mode="before")
    @classmethod
    def finite_parameter(cls, value: object) -> float | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("parameter must be a finite number")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("parameter must be a finite number")
        return number

    @model_validator(mode="after")
    def check_operands(self) -> GateSpec:
        expected = gate_arity(self.gate)
        if len(self.qubits) != expected:
            raise ValueError(
                f"gate '{self.gate}' expects {expected} qubit(s), got {len(self.qubits)}"
            )
        if len(set(self.qubits)) != len(self.qubits):
            raise ValueError(f"gate '{self.gate}' requires distinct qubits")
        if gate_takes_parameter(self.gate):
            if self.parameter is None:
                raise ValueError(f"gate '{self.gate}' requires a finite numeric parameter")
        elif self.parameter is not None:
            raise ValueError(f"gate '{self.gate}' does not take a parameter")
        return self


class MeasurementSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    qubit: StrictInt
    clbit: StrictInt


class CircuitSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    circuit_name: str = Field(min_length=1, max_length=200)
    num_qubits: StrictInt
    num_clbits: StrictInt
    gates: list[GateSpec] = Field(default_factory=list, max_length=512)
    measurements: list[MeasurementSpec] = Field(default_factory=list, max_length=64)
    description: str = Field(default="", max_length=2000)

    @field_validator("circuit_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("circuit_name must not be empty")
        return stripped

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def check_bounds(self) -> CircuitSpec:
        if self.num_qubits < 1:
            raise ValueError("num_qubits must be at least 1")
        if self.num_clbits < 0:
            raise ValueError("num_clbits must be non-negative")
        for index, gate in enumerate(self.gates):
            for qubit in gate.qubits:
                if qubit < 0 or qubit >= self.num_qubits:
                    raise ValueError(
                        f"gates[{index}] qubit index {qubit} is out of range "
                        f"for num_qubits={self.num_qubits}"
                    )
        seen_clbits: set[int] = set()
        for index, measurement in enumerate(self.measurements):
            if measurement.qubit < 0 or measurement.qubit >= self.num_qubits:
                raise ValueError(
                    f"measurements[{index}] qubit index {measurement.qubit} is out of range "
                    f"for num_qubits={self.num_qubits}"
                )
            if measurement.clbit < 0 or measurement.clbit >= self.num_clbits:
                raise ValueError(
                    f"measurements[{index}] clbit index {measurement.clbit} is out of range "
                    f"for num_clbits={self.num_clbits}"
                )
            if measurement.clbit in seen_clbits:
                raise ValueError(
                    f"measurements[{index}] clbit {measurement.clbit} is already used"
                )
            seen_clbits.add(measurement.clbit)
        return self

    def public_dict(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


def format_validation_errors(exc: ValidationError) -> list[str]:
    messages: list[str] = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error["loc"])
        message = str(error["msg"])
        prefix = "Value error, "
        if message.startswith(prefix):
            message = message[len(prefix) :]
        messages.append(f"{location}: {message}" if location else message)
    return messages


def inspect_spec(
    payload: Any,
    *,
    max_qubits: int,
    max_gates: int,
) -> tuple[CircuitSpec | None, list[str]]:
    if not isinstance(payload, dict):
        return None, ["circuit spec must be a JSON object"]
    try:
        spec = CircuitSpec.model_validate(payload)
    except ValidationError as exc:
        return None, format_validation_errors(exc)

    errors: list[str] = []
    if spec.num_qubits > max_qubits:
        errors.append(f"num_qubits {spec.num_qubits} exceeds MAX_QUBITS ({max_qubits})")
    if spec.num_clbits > max_qubits:
        errors.append(f"num_clbits {spec.num_clbits} exceeds MAX_QUBITS ({max_qubits})")
    if len(spec.gates) > max_gates:
        errors.append(f"circuit has {len(spec.gates)} gates, which exceeds the limit of {max_gates}")
    if errors:
        return None, errors
    return spec, []


def normalize_spec(payload: Any, *, max_qubits: int, max_gates: int) -> CircuitSpec:
    spec, errors = inspect_spec(payload, max_qubits=max_qubits, max_gates=max_gates)
    if spec is None:
        raise CircuitValidationError(errors)
    return spec
