import { describe, expect, it } from "vitest";
import { parseApiError } from "./api";

describe("parseApiError", () => {
  it("reads a configuration error without inventing a circuit", () => {
    const error = parseApiError(503, {
      error: {
        code: "configuration_error",
        message: "GROQ_API_KEY is not configured.",
        details: [],
      },
    });
    expect(error.status).toBe(503);
    expect(error.code).toBe("configuration_error");
    expect(error.message).toMatch(/GROQ_API_KEY/);
    expect(error.spec).toBeUndefined();
  });

  it("keeps validation details", () => {
    const error = parseApiError(422, {
      error: {
        code: "validation_error",
        message: "unsupported gate",
        details: ["gates.0: unsupported gate 'ccx'"],
      },
    });
    expect(error.details).toEqual(["gates.0: unsupported gate 'ccx'"]);
  });
});
