export type Gate = {
  gate: string;
  qubits: number[];
  parameter?: number | null;
};

export type Measurement = {
  qubit: number;
  clbit: number;
};

export type CircuitSpec = {
  circuit_name: string;
  num_qubits: number;
  num_clbits: number;
  gates: Gate[];
  measurements: Measurement[];
  description: string;
};

export type ValidationStatus = {
  valid: boolean;
  errors: string[];
};

export type Visualization = {
  format: string;
  svg: string;
};

export type SimulationMetadata = {
  num_qubits: number;
  num_clbits: number;
  gates_applied: string[];
  simulator: string;
  shots: number;
  provider?: string;
  model?: string;
  attempts?: number;
};

export type SimulationResponse = {
  spec: CircuitSpec;
  validation: ValidationStatus;
  shots: number;
  counts: Record<string, number>;
  probabilities: Record<string, number>;
  metadata: SimulationMetadata;
  visualization: Visualization;
};

export type GenerateResponse = SimulationResponse & {
  prompt: string;
  source: "llm";
};

export type HealthResponse = {
  status: string;
  service: { name: string; status: string };
  api: { status: string };
  quantum_simulator: { available: boolean; name: string; version?: string };
  pytorch: { available: boolean; version: string | null };
  llm: { provider: string; configured: boolean; model: string };
};

export type ResultSource = "llm" | "reference";

export type CircuitResult = {
  source: ResultSource;
  prompt: string;
  referenceLabel?: string;
  spec: CircuitSpec;
  validation: ValidationStatus;
  shots: number;
  counts: Record<string, number>;
  probabilities: Record<string, number>;
  metadata: SimulationMetadata;
  visualization: Visualization;
};
