import type {
  CircuitSpec,
  GenerateResponse,
  HealthResponse,
  LearnerExplanation,
  SimulationResponse,
} from "../types/circuit";

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: string[];
  readonly spec?: unknown;
  readonly learnerExplanation?: LearnerExplanation;

  constructor(
    status: number,
    code: string,
    message: string,
    details: string[] = [],
    spec?: unknown,
    learnerExplanation?: LearnerExplanation,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.spec = spec;
    this.learnerExplanation = learnerExplanation;
  }
}

type ErrorBody = {
  error?: {
    code?: string;
    message?: string;
    details?: string[];
  };
  spec?: unknown;
  learner_explanation?: LearnerExplanation;
};

export function parseApiError(status: number, body: unknown): ApiError {
  if (body && typeof body === "object" && "error" in body) {
    const payload = body as ErrorBody;
    return new ApiError(
      status,
      payload.error?.code ?? "request_failed",
      payload.error?.message ?? "Request failed.",
      payload.error?.details ?? [],
      payload.spec,
      payload.learner_explanation,
    );
  }
  return new ApiError(status, "request_failed", "Request failed.");
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBase}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(init?.body ? { "Content-Type": "application/json" } : {}),
        ...init?.headers,
      },
    });
  } catch {
    throw new ApiError(0, "network_error", "Could not reach the API. Is the backend running?");
  }

  const text = await response.text();
  let body: unknown = null;
  if (text) {
    try {
      body = JSON.parse(text) as unknown;
    } catch {
      throw new ApiError(response.status, "invalid_response", "The API returned a response that was not JSON.");
    }
  }
  if (!response.ok) {
    throw parseApiError(response.status, body);
  }
  return body as T;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/api/health");
}

export function simulate(spec: CircuitSpec, shots: number): Promise<SimulationResponse> {
  return request<SimulationResponse>("/api/circuits/simulate", {
    method: "POST",
    body: JSON.stringify({ spec, shots }),
  });
}

export function generateAndSimulate(prompt: string, shots: number): Promise<GenerateResponse> {
  return request<GenerateResponse>("/api/circuits/generate-and-simulate", {
    method: "POST",
    body: JSON.stringify({ prompt, shots }),
  });
}
