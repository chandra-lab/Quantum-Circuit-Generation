"""Plain-language explanations for Learner mode.

Every sentence is derived from the validated spec and the simulator counts.
No language model is called, so explanations work without a Groq key.
"""

from __future__ import annotations

import math
import re
from typing import Any

from app.quantum.gates import SUPPORTED_GATES
from app.schemas.circuit import CircuitSpec

MAX_LISTED_OUTCOMES = 4

KEY_IDEAS = {
    "superposition": (
        "Key idea: superposition. A Hadamard gate puts a qubit into an equal mix of 0 and 1, "
        "so each measurement is a fair coin flip."
    ),
    "bell": (
        "Key idea: entanglement (a Bell state). The two qubits are linked, so they always give "
        "the same result when measured, even though each result on its own is random."
    ),
    "ghz": (
        "Key idea: GHZ state. Entanglement is shared across {n} qubits, so they are either all 0 "
        "or all 1 together. Each run is random, but the qubits always agree."
    ),
    "bit_flip": (
        "Key idea: deterministic bit flip. The X gate works like a classical NOT, so the result "
        "is the same on every shot."
    ),
}

GENERIC_KEY_IDEA = (
    "In short: the gates prepare a quantum state, and measuring it many times shows how likely "
    "each result is. The histogram is an estimate of those chances."
)


def _qubit_list(qubits: list[int]) -> str:
    names = [f"qubit {q}" for q in qubits]
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + f" and {names[-1]}"


def _angle(parameter: float | None) -> str:
    value = parameter or 0.0
    degrees = math.degrees(value)
    return f"{value:g} radians (about {degrees:.0f} degrees)"


def _gate_sentence(gate: str, qubits: list[int], parameter: float | None, superposed: set[int]) -> str:
    q = qubits[0]
    if gate == "i":
        return f"I (identity) on qubit {q} does nothing. The qubit is left unchanged."
    if gate == "x":
        return (
            f"X on qubit {q} flips it: 0 becomes 1 and 1 becomes 0. "
            "It is the quantum version of a NOT gate."
        )
    if gate == "y":
        return (
            f"Y on qubit {q} flips it like X does and also changes its phase "
            "(a hidden sign that measurements in 0/1 do not show directly)."
        )
    if gate == "z":
        return (
            f"Z on qubit {q} leaves 0 alone and flips the sign (phase) of 1. "
            "On its own it does not change what you measure, but it matters when combined with other gates."
        )
    if gate == "h":
        if q in superposed:
            return (
                f"H (Hadamard) on qubit {q} mixes its 0 and 1 parts again. "
                "Applying H twice in a row undoes the first one."
            )
        return f"H (Hadamard) on qubit {q} puts it in an equal superposition of 0 and 1."
    if gate == "s":
        return (
            f"S on qubit {q} adds a quarter-turn phase to the 1 part of the qubit. "
            "It does not change measurement chances by itself."
        )
    if gate == "t":
        return (
            f"T on qubit {q} adds an eighth-turn phase to the 1 part of the qubit. "
            "It does not change measurement chances by itself."
        )
    if gate in {"rx", "ry"}:
        axis = gate[1].upper()
        return (
            f"{gate.upper()} on qubit {q} rotates it around the {axis} axis by {_angle(parameter)}. "
            "This changes the chances of measuring 0 or 1."
        )
    if gate == "rz":
        return (
            f"RZ on qubit {q} rotates it around the Z axis by {_angle(parameter)}. "
            "This only changes the phase, so it does not change measurement chances by itself."
        )
    control, target = qubits[0], qubits[1]
    if gate == "cx":
        sentence = (
            f"CX (CNOT) with control {control} and target {target} flips qubit {target} "
            f"when qubit {control} is 1"
        )
        if control in superposed:
            return sentence + ", which entangles them."
        return sentence + "."
    if gate == "cz":
        return (
            f"CZ on qubits {control} and {target} flips the sign (phase) when both qubits are 1. "
            "It does not change measurement chances by itself, but it can entangle qubits that are in superposition."
        )
    if gate == "swap":
        return f"SWAP exchanges the states of qubit {control} and qubit {target}."
    return f"{gate.upper()} acts on {_qubit_list(qubits)}."


def _step_sentences(spec: CircuitSpec) -> list[str]:
    if not spec.gates:
        return ["No gates are applied, so every qubit stays in its starting value 0."]
    superposed: set[int] = set()
    steps: list[str] = []
    for index, gate in enumerate(spec.gates, start=1):
        steps.append(f"Step {index}: {_gate_sentence(gate.gate, gate.qubits, gate.parameter, superposed)}")
        if gate.gate in {"h", "rx", "ry"}:
            superposed.add(gate.qubits[0])
        elif gate.gate == "cx" and gate.qubits[0] in superposed:
            superposed.add(gate.qubits[1])
        elif gate.gate == "swap":
            a, b = gate.qubits
            a_in, b_in = a in superposed, b in superposed
            superposed.discard(a)
            superposed.discard(b)
            if a_in:
                superposed.add(b)
            if b_in:
                superposed.add(a)
    return steps


def classify_pattern(spec: CircuitSpec) -> str | None:
    """Recognise a few textbook circuits from the gate sequence alone."""
    ops = [(gate.gate, tuple(gate.qubits)) for gate in spec.gates if gate.gate != "i"]
    if not ops:
        return None
    if all(name == "x" for name, _ in ops):
        return "bit_flip"
    if all(name == "h" for name, _ in ops):
        targets = [qubits[0] for _, qubits in ops]
        if len(set(targets)) == len(targets):
            return "superposition"
        return None
    first_name, first_qubits = ops[0]
    if first_name != "h" or len(ops) < 2 or any(name != "cx" for name, _ in ops[1:]):
        return None
    entangled = {first_qubits[0]}
    for _, (control, target) in ops[1:]:
        if control not in entangled or target in entangled:
            return None
        entangled.add(target)
    return "bell" if len(entangled) == 2 else "ghz"


def _overview(spec: CircuitSpec) -> str:
    qubits = "1 qubit" if spec.num_qubits == 1 else f"{spec.num_qubits} qubits"
    text = f'This circuit is called "{spec.circuit_name}" and uses {qubits}.'
    if spec.description:
        text += f" Its stated goal: {spec.description}"
    text += " Every qubit starts in the value 0, then the gates below are applied in order."
    return text


def _measurement_sentences(spec: CircuitSpec) -> list[str]:
    sentences = [
        f"Measuring qubit {m.qubit} reads it as 0 or 1 and stores that in classical bit {m.clbit}."
        for m in spec.measurements
    ]
    sentences.append(
        "Measurement ends any superposition: each run (shot) gives one definite 0 or 1 per measured qubit."
    )
    measured = {m.qubit for m in spec.measurements}
    unmeasured = [q for q in range(spec.num_qubits) if q not in measured]
    if unmeasured:
        verb = "is" if len(unmeasured) == 1 else "are"
        sentences.append(f"{_qubit_list(unmeasured).capitalize()} {verb} not measured, so they do not appear in the results.")
    written = {m.clbit for m in spec.measurements}
    unused = [c for c in range(spec.num_clbits) if c not in written]
    if unused:
        listed = ", ".join(str(c) for c in unused)
        sentences.append(f"Classical bit(s) {listed} are never written, so they always read 0.")
    return sentences


def _bit_order_note(spec: CircuitSpec) -> str:
    width = spec.num_clbits
    note = "How to read a bitstring: Qiskit writes classical bit 0 as the rightmost character."
    if width >= 2:
        example = "0" * (width - 1) + "1"
        note += f' For example, "{example}" means classical bit 0 is 1 and every other bit is 0.'
    identity = all(m.qubit == m.clbit for m in spec.measurements)
    if identity and spec.measurements:
        note += " In this circuit qubit n is stored in classical bit n, so the rightmost character is qubit 0."
    return note


def _percent(count: int, shots: int) -> str:
    return f"{count / shots * 100:.1f}%"


def _expected_outcomes(pattern: str | None, spec: CircuitSpec) -> tuple[str, ...] | None:
    width = spec.num_clbits
    if pattern in {"bell", "ghz"}:
        measured = {m.qubit for m in spec.measurements}
        ops = [g for g in spec.gates if g.gate != "i"]
        entangled = {ops[0].qubits[0]} | {g.qubits[1] for g in ops if g.gate == "cx"}
        if entangled != measured or len(spec.measurements) != width:
            return None
        return ("0" * width, "1" * width)
    return None


def _outcome_sentences(spec: CircuitSpec, shots: int, counts: dict[str, int], pattern: str | None) -> list[str]:
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    if not ranked:
        return ["The simulator returned no outcomes."]
    sentences = [f"The circuit was run {shots} times (shots)."]
    for bitstring, count in ranked[:MAX_LISTED_OUTCOMES]:
        sentences.append(f'"{bitstring}" appeared {count} times out of {shots} ({_percent(count, shots)}).')
    rest = ranked[MAX_LISTED_OUTCOMES:]
    if rest:
        rest_total = sum(count for _, count in rest)
        sentences.append(
            f"{len(rest)} other outcome(s) appeared {rest_total} times in total ({_percent(rest_total, shots)})."
        )

    if len(ranked) == 1:
        sentences.append(f'Every shot gave "{ranked[0][0]}", so this result is certain for this circuit.')
        if pattern == "bit_flip":
            sentences.append("That is exactly what the X gates predict: no randomness is involved.")
        return sentences

    expected = _expected_outcomes(pattern, spec)
    if expected and set(counts) <= set(expected):
        sentences.append(
            f'Only "{expected[0]}" and "{expected[1]}" appear because the entangled qubits always agree. '
            "Mixed results never show up."
        )
    elif pattern == "superposition":
        sentences.append(
            "Each qubit in superposition lands on 0 or 1 at random, so all of these outcomes are equally likely."
        )

    if pattern in {"bell", "ghz", "superposition"}:
        sentences.append(
            f"In theory the outcomes are split evenly. The small differences you see are shot noise: "
            f"random variation from taking only {shots} samples. More shots make the split closer to even."
        )
    else:
        sentences.append(
            f"Because each shot is random, the percentages will vary a little between runs. That variation is "
            f"shot noise from taking {shots} samples, and it shrinks as you use more shots."
        )
    return sentences


def explain_result(spec: CircuitSpec, *, shots: int, counts: dict[str, int]) -> dict[str, Any]:
    pattern = classify_pattern(spec)
    if pattern == "ghz":
        key_idea = KEY_IDEAS["ghz"].format(n=len({m.qubit for m in spec.measurements}) or spec.num_qubits)
    elif pattern:
        key_idea = KEY_IDEAS[pattern]
    else:
        key_idea = GENERIC_KEY_IDEA
    return {
        "pattern": pattern,
        "overview": _overview(spec),
        "steps": _step_sentences(spec),
        "measurements": _measurement_sentences(spec),
        "bit_order": _bit_order_note(spec),
        "outcome": _outcome_sentences(spec, shots, counts, pattern),
        "key_idea": key_idea,
        "validation": (
            "Validation passed: the circuit only uses supported gates, every qubit and classical bit it "
            "mentions exists, and the simulator was able to run it."
        ),
        "errors": [],
    }


_ERROR_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"unsupported gate '([^']*)'"),
        "The gate \"{0}\" is not one this app can run. Supported gates are: " + ", ".join(sorted(SUPPORTED_GATES)) + ".",
    ),
    (
        re.compile(r"gates\[(\d+)\] qubit index (-?\d+) is out of range for num_qubits=(\d+)"),
        "Gate number {0} (counting from 0) uses qubit {1}, but the circuit only has {2} qubit(s), numbered from 0.",
    ),
    (
        re.compile(r"measurements\[(\d+)\] qubit index (-?\d+) is out of range for num_qubits=(\d+)"),
        "Measurement number {0} (counting from 0) reads qubit {1}, but the circuit only has {2} qubit(s), numbered from 0.",
    ),
    (
        re.compile(r"measurements\[(\d+)\] clbit index (-?\d+) is out of range for num_clbits=(\d+)"),
        "Measurement number {0} (counting from 0) writes to classical bit {1}, but the circuit only has {2} classical bit(s), numbered from 0.",
    ),
    (
        re.compile(r"clbit (\d+) is already used"),
        "Two measurements write to classical bit {0}, so one result would overwrite the other. Each measurement needs its own classical bit.",
    ),
    (
        re.compile(r"gate '(\w+)' requires distinct qubits"),
        "The {0} gate was given the same qubit twice. A two-qubit gate needs two different qubits, for example a separate control and target.",
    ),
    (
        re.compile(r"gate '(\w+)' expects (\d+) qubit\(s\), got (\d+)"),
        "The {0} gate works on {1} qubit(s), but it was given {2}.",
    ),
    (
        re.compile(r"gate '(\w+)' requires a finite numeric parameter"),
        "The {0} gate is a rotation and needs an angle in radians, but none was given.",
    ),
    (
        re.compile(r"gate '(\w+)' does not take a parameter"),
        "The {0} gate does not use an angle, so the parameter should be removed.",
    ),
    (
        re.compile(r"parameter must be a finite number"),
        "A rotation angle must be an ordinary number. Infinity, NaN, or text is not allowed.",
    ),
    (
        re.compile(r"num_qubits (\d+) exceeds MAX_QUBITS \((\d+)\)"),
        "The circuit asks for {0} qubits, but this app allows at most {1}.",
    ),
    (
        re.compile(r"num_clbits (\d+) exceeds MAX_QUBITS \((\d+)\)"),
        "The circuit asks for {0} classical bits, but this app allows at most {1}.",
    ),
    (
        re.compile(r"circuit has (\d+) gates, which exceeds the limit of (\d+)"),
        "The circuit has {0} gates, which is more than the limit of {1}.",
    ),
    (
        re.compile(r"num_qubits must be at least 1"),
        "A circuit needs at least one qubit.",
    ),
    (
        re.compile(r"num_clbits must be non-negative"),
        "The number of classical bits cannot be negative.",
    ),
    (
        re.compile(r"circuit spec must be a JSON object"),
        "The circuit description must be a JSON object with fields such as circuit_name, num_qubits, and gates.",
    ),
    (
        re.compile(r"^([\w.\[\]]+): Field required"),
        "The required field \"{0}\" is missing from the circuit description.",
    ),
    (
        re.compile(r"^([\w.\[\]]+): Extra inputs are not permitted"),
        "The field \"{0}\" is not part of the circuit format, so it was rejected.",
    ),
    (
        re.compile(r"Simulation requires at least one measurement"),
        "The circuit never measures a qubit, so there are no results to count. Add at least one measurement.",
    ),
)


def explain_error_detail(detail: str) -> str:
    for pattern, template in _ERROR_RULES:
        match = pattern.search(detail)
        if match:
            return template.format(*match.groups())
    return f"The validator reported a problem it could not translate: {detail}"


def explain_errors(details: list[str], *, message: str = "") -> dict[str, Any]:
    items = details or ([message] if message else [])
    return {
        "pattern": None,
        "overview": "The circuit description could not be turned into a runnable circuit, so nothing was simulated.",
        "steps": [],
        "measurements": [],
        "bit_order": "",
        "outcome": [],
        "key_idea": "",
        "validation": (
            "Validation failed: the circuit breaks one or more rules the app checks before running anything. "
            "Each problem is explained below."
        ),
        "errors": [explain_error_detail(item) for item in items],
    }
