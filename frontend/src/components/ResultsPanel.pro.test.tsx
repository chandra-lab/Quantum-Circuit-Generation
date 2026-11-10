import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ResultsPanel } from "./ResultsPanel";
import { examplePrompts } from "../data/examples";
import type { CircuitResult } from "../types/circuit";

function bellResult(): CircuitResult {
  const bell = examplePrompts.find((example) => example.id === "bell");
  if (!bell?.spec) {
    throw new Error("bell spec missing");
  }
  return {
    source: "reference",
    prompt: bell.prompt,
    referenceLabel: bell.label,
    spec: bell.spec,
    validation: { valid: true, errors: [] },
    shots: 1000,
    counts: { "00": 503, "11": 497 },
    probabilities: { "00": 0.503, "11": 0.497 },
    metadata: {
      num_qubits: 2,
      num_clbits: 2,
      gates_applied: ["h", "cx"],
      simulator: "qiskit-aer",
      shots: 1000,
    },
    visualization: { format: "image/svg+xml", svg: "<svg></svg>" },
  };
}

describe("ResultsPanel in Pro mode", () => {
  it("renders the same markup as the original results panel", () => {
    const { container } = render(<ResultsPanel result={bellResult()} loading={null} />);
    expect(container.innerHTML).toMatchSnapshot();
  });
});
