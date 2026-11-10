import { useRef, useState, type DragEvent } from "react";
import { AttachmentChip } from "./AttachmentChip";
import { ACCEPT_ATTRIBUTE, DEFAULT_MAX_UPLOAD_MB, validateAttachment } from "../services/attachments";

type PromptFormProps = {
  prompt: string;
  shots: number;
  loading: boolean;
  disabled: boolean;
  attachment?: File | null;
  maxUploadMb?: number;
  onPromptChange: (value: string) => void;
  onShotsChange: (value: number) => void;
  onAttachmentChange?: (file: File | null) => void;
  onSubmit: () => void;
};

export function PromptForm({
  prompt,
  shots,
  loading,
  disabled,
  attachment = null,
  maxUploadMb = DEFAULT_MAX_UPLOAD_MB,
  onPromptChange,
  onShotsChange,
  onAttachmentChange,
  onSubmit,
}: PromptFormProps) {
  const fileInput = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [attachError, setAttachError] = useState<string | null>(null);
  const canAttach = Boolean(onAttachmentChange) && !disabled && !loading;

  const attach = (file: File | undefined) => {
    if (!file || !onAttachmentChange) {
      return;
    }
    const problem = validateAttachment(file, maxUploadMb);
    setAttachError(problem);
    if (!problem) {
      onAttachmentChange(file);
    }
  };

  const remove = () => {
    setAttachError(null);
    onAttachmentChange?.(null);
    if (fileInput.current) {
      fileInput.current.value = "";
    }
  };

  const hasDraggedFile = (event: DragEvent) => Array.from(event.dataTransfer.types).includes("Files");

  return (
    <form
      className={`panel transition ${dragging ? "ring-2 ring-navy/40" : ""}`}
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
      onDragOver={(event) => {
        if (canAttach && hasDraggedFile(event)) {
          event.preventDefault();
          setDragging(true);
        }
      }}
      onDragLeave={(event) => {
        if (!event.currentTarget.contains(event.relatedTarget as Node | null)) {
          setDragging(false);
        }
      }}
      onDrop={(event) => {
        if (!canAttach) {
          return;
        }
        event.preventDefault();
        setDragging(false);
        attach(event.dataTransfer.files[0]);
      }}
    >
      <label htmlFor="prompt" className="text-sm font-semibold text-navy">
        Natural language prompt
      </label>
      <textarea
        id="prompt"
        value={prompt}
        onChange={(event) => onPromptChange(event.target.value)}
        onPaste={(event) => {
          const pasted = event.clipboardData.files[0];
          if (pasted && canAttach) {
            event.preventDefault();
            attach(pasted);
          }
        }}
        rows={5}
        placeholder={
          attachment
            ? "Optional: add instructions to use alongside the attached file."
            : "Describe the quantum circuit you want to build."
        }
        className="mt-2 w-full resize-y rounded-md border border-line bg-white px-3 py-2 text-sm leading-relaxed outline-none ring-navy/30 focus:ring-2"
      />
      {onAttachmentChange ? (
        <div className="mt-3 space-y-2">
          {attachment ? (
            <AttachmentChip file={attachment} disabled={disabled || loading} onRemove={remove} />
          ) : (
            <div className="flex flex-wrap items-center gap-3">
              <button
                type="button"
                className="btn-secondary"
                disabled={!canAttach}
                onClick={() => fileInput.current?.click()}
              >
                Attach image or PDF
              </button>
              <span className="text-xs text-ink/60">
                Or drop or paste a file. PNG, JPEG, WebP, or PDF up to {maxUploadMb} MB.
              </span>
            </div>
          )}
          <input
            ref={fileInput}
            type="file"
            accept={ACCEPT_ATTRIBUTE}
            className="sr-only"
            tabIndex={-1}
            aria-label="Attach image or PDF file"
            disabled={!canAttach}
            onChange={(event) => {
              attach(event.target.files?.[0]);
              event.target.value = "";
            }}
          />
          {attachError ? (
            <p role="alert" className="text-sm text-red-800">
              {attachError}
            </p>
          ) : null}
        </div>
      ) : null}
      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <label className="text-sm text-ink/80">
          Shots
          <input
            type="number"
            min={1}
            value={shots}
            onChange={(event) => {
              const next = Number(event.target.value);
              if (Number.isInteger(next) && next > 0) {
                onShotsChange(next);
              }
            }}
            className="mt-1 block w-32 rounded-md border border-line bg-white px-3 py-2 font-mono text-sm outline-none ring-navy/30 focus:ring-2"
          />
        </label>
        <button
          type="submit"
          className="btn-primary"
          disabled={disabled || loading || (prompt.trim().length === 0 && !attachment)}
        >
          {loading ? "Generating…" : "Generate"}
        </button>
      </div>
      <p className="mt-3 text-xs leading-relaxed text-ink/60">
        Generate asks Groq for a JSON circuit spec, validates it, then simulates the circuit that
        the restricted gate map builds. An attached file is read first: PDF text on the server,
        images and scanned PDF pages with a Groq vision model. If the API key is missing, this
        button reports a configuration error and does not substitute a template.
      </p>
    </form>
  );
}
