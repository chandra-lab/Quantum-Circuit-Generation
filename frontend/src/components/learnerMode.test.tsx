import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { ErrorBanner } from "./ErrorBanner";
import { ResultsPanel } from "./ResultsPanel";
import { examplePrompts } from "../data/examples";
import { VIEW_MODE_STORAGE_KEY, readStoredViewMode } from "../hooks/useViewMode";
import { ApiError, parseApiError } from "../services/api";
import type { CircuitResult, LearnerExplanation } from "../types/circuit";

const bellExplanation: LearnerExplanation = {
  pattern: "bell",
  overview: 'This circuit is called "Bell State" and uses 2 qubits. Its stated goal: Creates an entangled Bell state.',
  steps: [
    "Step 1: H (Hadamard) on qubit 0 puts it in an equal superposition of 0 and 1.",
    "Step 2: CX (CNOT) with control 0 and target 1 flips qubit 1 when qubit 0 is 1, which entangles them.",
  ],
  measurements: ["Measuring qubit 0 reads it as 0 or 1 and stores that in classical bit 0."],
  bit_order: "How to read a bitstring: Qiskit writes classical bit 0 as the rightmost character.",
  outcome: ['"00" appeared 503 times out of 1000 (50.3%).', '"11" appeared 497 times out of 1000 (49.7%).'],
  key_idea: "Key idea: entanglement (a Bell state).",
  validation: "Validation passed: the circuit only uses supported gates.",
  errors: [],
};

function bellSpec() {
  const bell = examplePrompts.find((example) => example.id === "bell");
  if (!bell?.spec) {
    throw new Error("bell spec missing");
  }
  return { bell, spec: bell.spec };
}

function bellResult(withExplanation = true): CircuitResult {
  const { bell, spec } = bellSpec();
  return {
    source: "reference",
    prompt: bell.prompt,
    referenceLabel: bell.label,
    spec,
    validation: { valid: true, errors: [] },
    shots: 1000,
    counts: { "00": 503, "11": 497 },
    probabilities: { "00": 0.503, "11": 0.497 },
    metadata: { num_qubits: 2, num_clbits: 2, gates_applied: ["h", "cx"], simulator: "qiskit-aer", shots: 1000 },
    visualization: { format: "image/svg+xml", svg: "<svg></svg>" },
    learnerExplanation: withExplanation ? bellExplanation : undefined,
  };
}

function jsonResponse(body: unknown, status = 200) {
  return { ok: status < 400, status, text: async () => JSON.stringify(body) };
}

function mockApi() {
  const fetchMock = vi.fn(async (url: string) => {
    if (url.endsWith("/api/health")) {
      return jsonResponse({
        status: "ok",
        service: { name: "svc", status: "ok" },
        api: { status: "ok" },
        quantum_simulator: { available: true, name: "qiskit-aer" },
        pytorch: { available: false, version: null },
        llm: { provider: "groq", configured: true, model: "m" },
      });
    }
    const result = bellResult();
    return jsonResponse({
      spec: result.spec,
      validation: result.validation,
      shots: result.shots,
      counts: result.counts,
      probabilities: result.probabilities,
      metadata: result.metadata,
      visualization: result.visualization,
      learner_explanation: bellExplanation,
    });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("Learner / Pro toggle", () => {
  it("defaults to Pro and switches to Learner", async () => {
    mockApi();
    render(<App />);
    const group = screen.getByRole("radiogroup", { name: /view mode/i });
    const pro = within(group).getByRole("radio", { name: "Pro" });
    const learner = within(group).getByRole("radio", { name: "Learner" });
    expect(pro.getAttribute("aria-checked")).toBe("true");
    expect(learner.getAttribute("aria-checked")).toBe("false");

    fireEvent.click(screen.getAllByRole("button", { name: "Simulate reference" })[0]);
    await screen.findByText("Bell State");
    expect(screen.getByText("Spec JSON")).toBeTruthy();
    expect(screen.queryByText(/in plain language/)).toBeNull();
    expect(screen.queryByText("Show technical details")).toBeNull();

    fireEvent.click(learner);
    expect(learner.getAttribute("aria-checked")).toBe("true");
    expect(pro.getAttribute("aria-checked")).toBe("false");
    expect(screen.getByText(/in plain language/)).toBeTruthy();
    expect(screen.getByText(bellExplanation.steps[1])).toBeTruthy();
    expect(screen.getByText('"00" appeared 503 times out of 1000 (50.3%).')).toBeTruthy();
    expect(screen.getByText(/rightmost character/)).toBeTruthy();
    expect(screen.getByText("Show technical details")).toBeTruthy();
    expect(screen.getByLabelText("Measurement histogram")).toBeTruthy();
    expect(screen.getByText("Show technical details").closest("details")?.open).toBe(false);
  });

  it("persists the chosen mode across reloads", async () => {
    mockApi();
    const first = render(<App />);
    fireEvent.click(screen.getByRole("radio", { name: "Learner" }));
    expect(window.localStorage.getItem(VIEW_MODE_STORAGE_KEY)).toBe("learner");
    first.unmount();

    render(<App />);
    expect(screen.getByRole("radio", { name: "Learner" }).getAttribute("aria-checked")).toBe("true");
    await waitFor(() => expect(screen.getByRole("radio", { name: "Pro" }).getAttribute("tabindex")).toBe("-1"));
  });

  it("is keyboard operable with arrow keys", () => {
    mockApi();
    render(<App />);
    const pro = screen.getByRole("radio", { name: "Pro" });
    const learner = screen.getByRole("radio", { name: "Learner" });
    expect(pro.getAttribute("tabindex")).toBe("0");
    fireEvent.keyDown(pro, { key: "ArrowLeft" });
    expect(learner.getAttribute("aria-checked")).toBe("true");
    expect(document.activeElement).toBe(learner);
    fireEvent.keyDown(learner, { key: "ArrowRight" });
    expect(pro.getAttribute("aria-checked")).toBe("true");
    expect(window.localStorage.getItem(VIEW_MODE_STORAGE_KEY)).toBe("pro");
  });

  it("falls back to Pro for a missing or unknown stored value", () => {
    expect(readStoredViewMode()).toBe("pro");
    window.localStorage.setItem(VIEW_MODE_STORAGE_KEY, "expert");
    expect(readStoredViewMode()).toBe("pro");
  });
});

describe("ResultsPanel in Learner mode", () => {
  it("shows the explanation, the diagram, and the histogram", () => {
    render(<ResultsPanel result={bellResult()} loading={null} mode="learner" />);
    expect(screen.getByText(bellExplanation.key_idea)).toBeTruthy();
    expect(screen.getByText(bellExplanation.overview)).toBeTruthy();
    expect(screen.getByText(bellExplanation.validation)).toBeTruthy();
    expect(screen.getByRole("img", { name: /Qiskit circuit diagram/ })).toBeTruthy();
    expect(screen.getByLabelText("Measurement histogram")).toBeTruthy();
  });

  it("explains how to get explanations when the backend omits them", () => {
    render(<ResultsPanel result={bellResult(false)} loading={null} mode="learner" />);
    expect(screen.getByText(/did not send a plain-language explanation/)).toBeTruthy();
  });

  it("does not show learner text in Pro mode", () => {
    render(<ResultsPanel result={bellResult()} loading={null} mode="pro" />);
    expect(screen.queryByText(bellExplanation.key_idea)).toBeNull();
  });
});

describe("ErrorBanner learner explanation", () => {
  const explanation: LearnerExplanation = {
    pattern: null,
    overview: "The circuit description could not be turned into a runnable circuit, so nothing was simulated.",
    steps: [],
    measurements: [],
    bit_order: "",
    outcome: [],
    key_idea: "",
    validation: "Validation failed: the circuit breaks one or more rules.",
    errors: ['The gate "toffoli" is not one this app can run.'],
  };

  it("parses learner_explanation from an error body", () => {
    const error = parseApiError(422, {
      error: { code: "validation_error", message: "unsupported gate 'toffoli'", details: ["gates.0.gate: unsupported gate 'toffoli'"] },
      learner_explanation: explanation,
    });
    expect(error.learnerExplanation?.errors[0]).toMatch(/toffoli/);
  });

  it("shows plain-language errors only in Learner mode", () => {
    const error = new ApiError(422, "validation_error", "unsupported gate 'toffoli'", ["raw detail"], undefined, explanation);
    const { rerender } = render(<ErrorBanner error={error} mode="pro" />);
    expect(screen.queryByText("What this means")).toBeNull();
    rerender(<ErrorBanner error={error} mode="learner" />);
    expect(screen.getByText("What this means")).toBeTruthy();
    expect(screen.getByText(explanation.validation)).toBeTruthy();
    expect(screen.getByText(explanation.errors[0])).toBeTruthy();
    expect(screen.getByText("raw detail")).toBeTruthy();
  });
});
