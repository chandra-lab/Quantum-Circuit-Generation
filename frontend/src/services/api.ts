import type {
  CircuitSpec,
  Extraction,
  GenerateResponse,
  HealthResponse,
  LearnerExplanation,
  SimulationResponse,
} from "../types/circuit";
import { attachmentType } from "./attachments";

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: string[];
  readonly spec?: unknown;
  readonly learnerExplanation?: LearnerExplanation;
  /** Text read from an uploaded file before the request failed. */
  extraction?: Extraction;

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
  extraction?: Extraction;
};

export function parseApiError(status: number, body: unknown): ApiError {
  if (body && typeof body === "object" && "error" in body) {
    const payload = body as ErrorBody;
    const error = new ApiError(
      status,
      payload.error?.code ?? "request_failed",
      payload.error?.message ?? "Request failed.",
      payload.error?.details ?? [],
      payload.spec,
      payload.learner_explanation,
    );
    error.extraction = payload.extraction;
    return error;
  }
  if (status === 413) {
    return new ApiError(status, "file_too_large", "The request is larger than the server accepts.");
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
        ...(typeof init?.body === "string" ? { "Content-Type": "application/json" } : {}),
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
      if (!response.ok) {
        throw parseApiError(response.status, null);
      }
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

/** Multipart request. The browser sets the boundary, so Content-Type is left unset. */
export function generateFromFile(file: File, prompt: string, shots: number): Promise<GenerateResponse> {
  const form = new FormData();
  const type = attachmentType(file);
  form.append("file", type === file.type ? file : new Blob([file], { type }), file.name);
  if (prompt.trim()) {
    form.append("prompt", prompt.trim());
  }
  form.append("shots", String(shots));
  return request<GenerateResponse>("/api/circuits/generate-from-file", {
    method: "POST",
    body: form,
  });
}
