import type { CircuitSpec } from "../types/circuit";

/**
 * Prompt copy and predefined specs. The four runnable specs match
 * backend/app/quantum/examples.py and are not language-model output.
 */

const bell: CircuitSpec = {
  circuit_name: "Bell State",
  num_qubits: 2,
  num_clbits: 2,
  gates: [
    { gate: "h", qubits: [0] },
    { gate: "cx", qubits: [0, 1] },
  ],
  measurements: [
    { qubit: 0, clbit: 0 },
    { qubit: 1, clbit: 1 },
  ],
  description: "Creates an entangled Bell state.",
};

const superposition: CircuitSpec = {
  circuit_name: "Superposition",
  num_qubits: 1,
  num_clbits: 1,
  gates: [{ gate: "h", qubits: [0] }],
  measurements: [{ qubit: 0, clbit: 0 }],
  description: "Applies a Hadamard gate to create an equal superposition, then measures.",
};

const ghz: CircuitSpec = {
  circuit_name: "GHZ State",
  num_qubits: 3,
  num_clbits: 3,
  gates: [
    { gate: "h", qubits: [0] },
    { gate: "cx", qubits: [0, 1] },
    { gate: "cx", qubits: [0, 2] },
  ],
  measurements: [
    { qubit: 0, clbit: 0 },
    { qubit: 1, clbit: 1 },
    { qubit: 2, clbit: 2 },
  ],
  description: "Prepares a three-qubit GHZ state and measures all qubits.",
};

const bitFlip: CircuitSpec = {
  circuit_name: "Bit Flip",
  num_qubits: 1,
  num_clbits: 1,
  gates: [{ gate: "x", qubits: [0] }],
  measurements: [{ qubit: 0, clbit: 0 }],
  description: "Flips |0> to |1> with an X gate and measures.",
};

export type ExamplePrompt = {
  id: string;
  label: string;
  prompt: string;
  description: string;
  runnableWithoutLlm: boolean;
  spec: CircuitSpec | null;
};

export const examplePrompts: ExamplePrompt[] = [
  {
    id: "bell",
    label: "Bell state",
    prompt: "Generate a Bell State using two qubits.",
    description: "Two qubits, Hadamard on qubit 0, CNOT from 0 to 1, measure both.",
    runnableWithoutLlm: true,
    spec: bell,
  },
  {
    id: "superposition",
    label: "Superposition",
    prompt: "Create a quantum superposition using a Hadamard gate.",
    description: "One qubit, Hadamard, then measure.",
    runnableWithoutLlm: true,
    spec: superposition,
  },
  {
    id: "ghz",
    label: "GHZ state (three qubits)",
    prompt:
      "Create a quantum circuit with three qubits that prepares a GHZ state: Hadamard on qubit 0, CNOT from 0 to 1, CNOT from 0 to 2, and measure all three qubits.",
    description: "Three-qubit GHZ state: H on 0, CNOT 0→1, CNOT 0→2, measure all.",
    runnableWithoutLlm: true,
    spec: ghz,
  },
  {
    id: "x-h-cnot",
    label: "X, H, and CNOT",
    prompt: "Apply X, H, and CNOT gates to a quantum circuit.",
    description: "Open-ended prompt for the language model. No predefined reference circuit.",
    runnableWithoutLlm: false,
    spec: null,
  },
  {
    id: "measurement",
    label: "Measurement circuit",
    prompt: "Create a quantum measurement circuit.",
    description: "Open-ended prompt for the language model. No predefined reference circuit.",
    runnableWithoutLlm: false,
    spec: null,
  },
  {
    id: "bit-flip",
    label: "Quantum bit flip",
    prompt:
      "Quantum bit flip: prepare one qubit in the zero state, apply a single X gate, and measure that qubit.",
    description: "One qubit, X, then measure. The outcome is |1>.",
    runnableWithoutLlm: true,
    spec: bitFlip,
  },
];

export const referenceCircuits = examplePrompts.filter((example) => example.runnableWithoutLlm && example.spec);
