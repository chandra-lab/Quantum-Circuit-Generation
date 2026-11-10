import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ExamplePromptList } from "./ExamplePromptList";
import { Histogram } from "./Histogram";
import { ResultsPanel } from "./ResultsPanel";
import { examplePrompts } from "../data/examples";
import type { CircuitResult } from "../types/circuit";

describe("Histogram", () => {
  it("draws one bar for each measured outcome", () => {
    render(<Histogram counts={{ "00": 48, "11": 52 }} />);
    expect(screen.getByTestId("bar-00")).toBeTruthy();
    expect(screen.getByTestId("bar-11")).toBeTruthy();
    expect(screen.getByText("00")).toBeTruthy();
    expect(screen.getByText("11")).toBeTruthy();
  });
});

describe("ExamplePromptList", () => {
  it("fills the box with the GHZ prompt", () => {
    const selected: string[] = [];
    render(
      <ExamplePromptList
        prompts={examplePrompts}
        disabled={false}
        onSelect={(prompt) => selected.push(prompt)}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: /GHZ state/i }));
    expect(selected[0]).toMatch(/GHZ/);
    expect(selected[0]).toMatch(/three qubits/);
  });
});

describe("ResultsPanel", () => {
  it("labels a reference run as not LLM output", () => {
    const bell = examplePrompts.find((example) => example.id === "bell");
    if (!bell?.spec) {
      throw new Error("bell spec missing");
    }
    const result: CircuitResult = {
      source: "reference",
      prompt: bell.prompt,
      referenceLabel: bell.label,
      spec: bell.spec,
      validation: { valid: true, errors: [] },
      shots: 1000,
      counts: { "00": 500, "11": 500 },
      probabilities: { "00": 0.5, "11": 0.5 },
      metadata: {
        num_qubits: 2,
        num_clbits: 2,
        gates_applied: ["h", "cx"],
        simulator: "qiskit-aer",
        shots: 1000,
      },
      visualization: { format: "image/svg+xml", svg: "<svg></svg>" },
    };
    render(<ResultsPanel result={result} loading={null} />);
    expect(screen.getByText(/Predefined reference circuit — not LLM output/)).toBeTruthy();
    expect(screen.getByText(bell.prompt)).toBeTruthy();
    expect(screen.getByText("Bell State")).toBeTruthy();
    expect(screen.getByText("qiskit-aer")).toBeTruthy();
  });
});

describe("ResultsPanel with a file prompt", () => {
  it("shows the extracted text and offers edit and regenerate", () => {
    const bell = examplePrompts.find((example) => example.id === "bell");
    if (!bell?.spec) {
      throw new Error("bell spec missing");
    }
    const onEdit = vi.fn();
    const result: CircuitResult = {
      source: "llm",
      prompt: "Uploaded file: question.pdf",
      spec: bell.spec,
      validation: { valid: true, errors: [] },
      shots: 100,
      counts: { "00": 50, "11": 50 },
      probabilities: { "00": 0.5, "11": 0.5 },
      metadata: { num_qubits: 2, num_clbits: 2, gates_applied: ["h", "cx"], simulator: "qiskit-aer", shots: 100 },
      visualization: { format: "image/svg+xml", svg: "<svg></svg>" },
      extraction: {
        filename: "question.pdf",
        media_type: "application/pdf",
        method: "pdf_text",
        text: "Prepare a Bell pair and measure both qubits.",
        truncated: false,
        pages_read: 10,
        total_pages: 12,
      },
    };
    render(<ResultsPanel result={result} loading={null} onEditExtraction={onEdit} />);
    expect(screen.getByText("Extracted from your file")).toBeTruthy();
    expect(screen.getByText("Prepare a Bell pair and measure both qubits.")).toBeTruthy();
    expect(screen.getByText(/Read the first 10 of 12 pages/)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Edit and regenerate" }));
    expect(onEdit).toHaveBeenCalledWith("Prepare a Bell pair and measure both qubits.");
  });
});
