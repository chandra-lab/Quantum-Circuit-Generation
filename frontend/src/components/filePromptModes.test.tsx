import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "../App";
import { examplePrompts } from "../data/examples";
import type { LearnerExplanation, ViewMode } from "../types/circuit";

const EXTRACTED = "Prepare a Bell pair on two qubits and measure both.";

const explanation: LearnerExplanation = {
  pattern: "bell",
  overview: "This circuit makes a Bell pair from the uploaded question.",
  steps: ["Step 1: H on qubit 0.", "Step 2: CX from qubit 0 to qubit 1."],
  measurements: ["Both qubits are measured."],
  bit_order: "Qiskit writes classical bit 0 as the rightmost character.",
  outcome: ['"00" appeared 50 times out of 100 (50.0%).'],
  key_idea: "Key idea: the uploaded question asks for entanglement.",
  validation: "Validation passed.",
  errors: [],
};

function jsonResponse(body: unknown, status = 200) {
  return { ok: status < 400, status, text: async () => JSON.stringify(body) };
}

function mockApi() {
  const bell = examplePrompts.find((example) => example.id === "bell");
  const fetchMock = vi.fn(async (url: string, _init?: RequestInit) => {
    if (url.endsWith("/api/health")) {
      return jsonResponse({
        status: "ok",
        service: { name: "svc", status: "ok" },
        api: { status: "ok" },
        quantum_simulator: { available: true, name: "qiskit-aer" },
        pytorch: { available: false, version: null },
        llm: { provider: "groq", configured: true, model: "m" },
        uploads: { max_upload_mb: 10, max_pdf_pages: 10, media_types: [] },
      });
    }
    return jsonResponse({
      prompt: "Uploaded file: question.pdf",
      source: "llm",
      spec: bell?.spec,
      validation: { valid: true, errors: [] },
      shots: 100,
      counts: { "00": 50, "11": 50 },
      probabilities: { "00": 0.5, "11": 0.5 },
      metadata: { num_qubits: 2, num_clbits: 2, gates_applied: ["h", "cx"], simulator: "qiskit-aer", shots: 100 },
      visualization: { format: "image/svg+xml", svg: "<svg></svg>" },
      learner_explanation: explanation,
      extraction: {
        filename: "question.pdf",
        media_type: "application/pdf",
        method: "pdf_text",
        text: EXTRACTED,
        truncated: false,
        pages_read: 1,
        total_pages: 1,
      },
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

describe.each<ViewMode>(["pro", "learner"])("file prompt in %s mode", (mode) => {
  it("attaches, generates, shows the extracted text, and edits and regenerates", async () => {
    const fetchMock = mockApi();
    render(<App />);
    const group = screen.getByRole("radiogroup", { name: /view mode/i });
    fireEvent.click(within(group).getByRole("radio", { name: mode === "pro" ? "Pro" : "Learner" }));

    const file = new File(["%PDF-1.4"], "question.pdf", { type: "application/pdf" });
    fireEvent.change(screen.getByLabelText("Attach image or PDF file"), { target: { files: [file] } });
    expect(screen.getByTestId("attachment-chip").textContent).toContain("question.pdf");

    fireEvent.click(screen.getByRole("button", { name: "Generate" }));
    await screen.findByText("Extracted from your file");

    const call = fetchMock.mock.calls.find(([url]) => url.endsWith("/api/circuits/generate-from-file"));
    expect(call?.[1]?.body).toBeInstanceOf(FormData);
    expect(screen.getAllByText("Extracted from your file")).toHaveLength(1);
    expect(screen.getByText(EXTRACTED)).toBeTruthy();
    if (mode === "learner") {
      expect(screen.getByText(explanation.key_idea)).toBeTruthy();
      expect(screen.getByText(explanation.steps[1])).toBeTruthy();
    } else {
      expect(screen.getByText("Spec JSON")).toBeTruthy();
      expect(screen.queryByText(explanation.key_idea)).toBeNull();
    }

    fireEvent.click(screen.getByRole("button", { name: "Edit and regenerate" }));
    expect((screen.getByLabelText("Natural language prompt") as HTMLTextAreaElement).value).toBe(EXTRACTED);
    expect(screen.queryByTestId("attachment-chip")).toBeNull();
  });
});
