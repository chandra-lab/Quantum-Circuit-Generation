import type { Extraction } from "../types/circuit";

type ExtractionNoticeProps = {
  extraction: Extraction;
  onEdit?: (text: string) => void;
};

const methodLabels: Record<Extraction["method"], string> = {
  pdf_text: "PDF text layer",
  pdf_vision: "Scanned PDF read by the vision model",
  image_vision: "Image read by the vision model",
};

function pageNote(extraction: Extraction): string | null {
  if (extraction.pages_read === null || extraction.total_pages === null) {
    return null;
  }
  if (extraction.pages_read < extraction.total_pages) {
    return `Read the first ${extraction.pages_read} of ${extraction.total_pages} pages.`;
  }
  return `Read ${extraction.total_pages} ${extraction.total_pages === 1 ? "page" : "pages"}.`;
}

export function ExtractionNotice({ extraction, onEdit }: ExtractionNoticeProps) {
  const pages = pageNote(extraction);
  return (
    <section
      className="rounded-lg border border-line bg-paper px-3 py-3"
      aria-labelledby="extraction-heading"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 id="extraction-heading" className="text-xs font-semibold uppercase tracking-wide text-ink/50">
          Extracted from your file
        </h3>
        {onEdit ? (
          <button
            type="button"
            className="text-xs font-semibold text-navy underline-offset-2 hover:underline"
            onClick={() => onEdit(extraction.text)}
          >
            Edit and regenerate
          </button>
        ) : null}
      </div>
      <p className="mt-1 text-xs text-ink/60">
        {extraction.filename} · {methodLabels[extraction.method]}
        {pages ? ` · ${pages}` : ""}
        {extraction.truncated ? " · Text was shortened before generation." : ""}
      </p>
      <p className="mt-2 max-h-48 overflow-y-auto whitespace-pre-wrap text-sm leading-relaxed">
        {extraction.text}
      </p>
    </section>
  );
}
