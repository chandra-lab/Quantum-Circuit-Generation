import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PromptForm } from "./PromptForm";

function Harness({ onAttachmentChange }: { onAttachmentChange?: (file: File | null) => void }) {
  const [prompt, setPrompt] = useState("");
  const [attachment, setAttachment] = useState<File | null>(null);
  return (
    <PromptForm
      prompt={prompt}
      shots={1000}
      loading={false}
      disabled={false}
      attachment={attachment}
      maxUploadMb={1}
      onPromptChange={setPrompt}
      onShotsChange={() => undefined}
      onAttachmentChange={(file) => {
        setAttachment(file);
        onAttachmentChange?.(file);
      }}
      onSubmit={() => undefined}
    />
  );
}

function pickFile(file: File) {
  fireEvent.change(screen.getByLabelText("Attach image or PDF file"), { target: { files: [file] } });
}

const originalCreateObjectURL = URL.createObjectURL;
const originalRevokeObjectURL = URL.revokeObjectURL;

afterEach(() => {
  cleanup();
  URL.createObjectURL = originalCreateObjectURL;
  URL.revokeObjectURL = originalRevokeObjectURL;
});

describe("PromptForm attachments", () => {
  it("shows a chip with a thumbnail for an attached image and enables Generate", () => {
    URL.createObjectURL = vi.fn(() => "blob:preview");
    URL.revokeObjectURL = vi.fn();
    render(<Harness />);
    const generate = screen.getByRole("button", { name: "Generate" }) as HTMLButtonElement;
    expect(generate.disabled).toBe(true);

    pickFile(new File(["png"], "bell.png", { type: "image/png" }));

    const chip = screen.getByTestId("attachment-chip");
    expect(chip.textContent).toContain("bell.png");
    expect(chip.querySelector("img")?.getAttribute("src")).toBe("blob:preview");
    expect(generate.disabled).toBe(false);
  });

  it("removes the attachment", () => {
    const changes: Array<File | null> = [];
    render(<Harness onAttachmentChange={(file) => changes.push(file)} />);
    pickFile(new File(["%PDF-1.4"], "question.pdf", { type: "application/pdf" }));
    expect(screen.getByTestId("attachment-chip").textContent).toContain("question.pdf");

    fireEvent.click(screen.getByRole("button", { name: "Remove question.pdf" }));

    expect(screen.queryByTestId("attachment-chip")).toBeNull();
    expect(changes.at(-1)).toBeNull();
    expect(screen.getByRole("button", { name: "Attach image or PDF" })).toBeTruthy();
  });

  it("rejects an unsupported type", () => {
    const changes: Array<File | null> = [];
    render(<Harness onAttachmentChange={(file) => changes.push(file)} />);
    pickFile(new File(["hello"], "notes.txt", { type: "text/plain" }));
    expect(screen.getByRole("alert").textContent).toMatch(/notes\.txt is not a PNG, JPEG, WebP, or PDF/);
    expect(screen.queryByTestId("attachment-chip")).toBeNull();
    expect(changes).toEqual([]);
  });

  it("rejects a file over the size limit", () => {
    render(<Harness />);
    const big = new File([new Uint8Array(1024 * 1024 + 1)], "big.png", { type: "image/png" });
    pickFile(big);
    expect(screen.getByRole("alert").textContent).toMatch(/limit is 1 MB/);
    expect(screen.queryByTestId("attachment-chip")).toBeNull();
  });

  it("accepts a dropped file and a pasted image", () => {
    render(<Harness />);
    const form = screen.getByRole("button", { name: "Generate" }).closest("form") as HTMLFormElement;
    const dropped = new File(["%PDF-1.4"], "dropped.pdf", { type: "application/pdf" });
    fireEvent.drop(form, { dataTransfer: { files: [dropped], types: ["Files"] } });
    expect(screen.getByTestId("attachment-chip").textContent).toContain("dropped.pdf");

    fireEvent.click(screen.getByRole("button", { name: "Remove dropped.pdf" }));
    const pasted = new File(["jpg"], "clipboard.jpg", { type: "image/jpeg" });
    fireEvent.paste(screen.getByLabelText("Natural language prompt"), { clipboardData: { files: [pasted] } });
    expect(screen.getByTestId("attachment-chip").textContent).toContain("clipboard.jpg");
  });
});
