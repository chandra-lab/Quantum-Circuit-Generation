import { describe, expect, it } from "vitest";
import { examplePrompts, referenceCircuits } from "./examples";

describe("reference circuits", () => {
  it("ships Bell, superposition, GHZ, and bit flip", () => {
    const ids = referenceCircuits.map((circuit) => circuit.id);
    expect(ids).toEqual(["bell", "superposition", "ghz", "bit-flip"]);
  });

  it("defines the three-qubit example as a GHZ state", () => {
    const ghz = examplePrompts.find((example) => example.id === "ghz");
    expect(ghz?.label.toLowerCase()).toContain("ghz");
    expect(ghz?.spec?.num_qubits).toBe(3);
    expect(ghz?.spec?.gates.map((gate) => gate.gate)).toEqual(["h", "cx", "cx"]);
    expect(ghz?.spec?.gates[1]?.qubits).toEqual([0, 1]);
    expect(ghz?.spec?.gates[2]?.qubits).toEqual([0, 2]);
    expect(ghz?.spec?.measurements).toHaveLength(3);
  });

  it("keeps open prompts out of the reference set", () => {
    const open = examplePrompts.filter((example) => !example.runnableWithoutLlm);
    expect(open.map((example) => example.id)).toEqual(["x-h-cnot", "measurement"]);
    expect(open.every((example) => example.spec === null)).toBe(true);
  });
});
