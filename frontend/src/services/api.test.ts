import { afterEach, describe, expect, it, vi } from "vitest";
import { generateFromFile, parseApiError } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("generateFromFile", () => {
  it("sends the file, prompt, and shots as multipart form data", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) =>
      new Response(JSON.stringify({ prompt: "x", source: "llm" }), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);
    const file = new File(["%PDF-1.4"], "question.pdf", { type: "application/pdf" });

    await generateFromFile(file, "  use three qubits  ", 500);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/circuits/generate-from-file");
    expect(init?.method).toBe("POST");
    const body = init?.body;
    expect(body).toBeInstanceOf(FormData);
    const form = body as FormData;
    const sent = form.get("file") as File;
    expect(sent.name).toBe("question.pdf");
    expect(sent.type).toBe("application/pdf");
    expect(form.get("prompt")).toBe("use three qubits");
    expect(form.get("shots")).toBe("500");
    expect(new Headers(init?.headers).has("Content-Type")).toBe(false);
  });

  it("fills in a missing file type from the extension", async () => {
    const fetchMock = vi.fn(async (_input: RequestInfo | URL, _init?: RequestInit) =>
      new Response("{}", { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await generateFromFile(new File(["webp"], "circuit.webp"), "", 100);

    const form = fetchMock.mock.calls[0][1]?.body as FormData;
    expect((form.get("file") as File).type).toBe("image/webp");
    expect(form.has("prompt")).toBe(false);
  });

  it("keeps extracted text on a configuration error", async () => {
    const extraction = {
      filename: "question.pdf",
      media_type: "application/pdf",
      method: "pdf_text",
      text: "Generate a Bell state.",
      truncated: false,
      pages_read: 1,
      total_pages: 1,
    };
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            error: { code: "configuration_error", message: "GROQ_API_KEY is not configured.", details: [] },
            extraction,
          }),
          { status: 503 },
        ),
      ),
    );
    const file = new File(["%PDF-1.4"], "question.pdf", { type: "application/pdf" });
    await expect(generateFromFile(file, "", 100)).rejects.toMatchObject({
      code: "configuration_error",
      extraction,
    });
  });

  it("maps an nginx HTML 413 to file_too_large", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("<html>413</html>", { status: 413 })));
    const file = new File(["png"], "big.png", { type: "image/png" });
    await expect(generateFromFile(file, "", 100)).rejects.toMatchObject({ status: 413, code: "file_too_large" });
  });
});

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
