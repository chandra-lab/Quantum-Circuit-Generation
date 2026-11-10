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

export type LearnerExplanation = {
  pattern: "superposition" | "bell" | "ghz" | "bit_flip" | null;
  overview: string;
  steps: string[];
  measurements: string[];
  bit_order: string;
  outcome: string[];
  key_idea: string;
  validation: string;
  errors: string[];
};

export type SimulationResponse = {
  spec: CircuitSpec;
  validation: ValidationStatus;
  shots: number;
  counts: Record<string, number>;
  probabilities: Record<string, number>;
  metadata: SimulationMetadata;
  visualization: Visualization;
  learner_explanation?: LearnerExplanation;
  extraction?: Extraction;
};

export type ExtractionMethod = "pdf_text" | "pdf_vision" | "image_vision";

export type Extraction = {
  filename: string;
  media_type: string;
  method: ExtractionMethod;
  text: string;
  truncated: boolean;
  pages_read: number | null;
  total_pages: number | null;
};

export type GenerateResponse = SimulationResponse & {
  prompt: string;
  source: "llm";
  extraction?: Extraction;
};

export type HealthResponse = {
  status: string;
  service: { name: string; status: string };
  api: { status: string };
  quantum_simulator: { available: boolean; name: string; version?: string };
  pytorch: { available: boolean; version: string | null };
  llm: { provider: string; configured: boolean; model: string; vision_model?: string };
  uploads?: { max_upload_mb: number; max_pdf_pages: number; media_types: string[] };
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
  learnerExplanation?: LearnerExplanation;
  extraction?: Extraction;
};

export type ViewMode = "learner" | "pro";
