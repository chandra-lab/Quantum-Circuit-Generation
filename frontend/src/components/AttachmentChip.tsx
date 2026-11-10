import { useEffect, useState } from "react";
import { formatBytes, isImage } from "../services/attachments";

type AttachmentChipProps = {
  file: File;
  disabled: boolean;
  onRemove: () => void;
};

export function AttachmentChip({ file, disabled, onRemove }: AttachmentChipProps) {
  const [thumbnail, setThumbnail] = useState<string | null>(null);

  useEffect(() => {
    if (!isImage(file) || typeof URL.createObjectURL !== "function") {
      setThumbnail(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setThumbnail(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  return (
    <div
      className="inline-flex max-w-full items-center gap-3 rounded-lg border border-line bg-paper px-2 py-2"
      data-testid="attachment-chip"
    >
      {thumbnail ? (
        <img src={thumbnail} alt="" className="h-10 w-10 flex-none rounded object-cover" />
      ) : (
        <span
          aria-hidden="true"
          className="flex h-10 w-10 flex-none items-center justify-center rounded bg-copper/10 text-[11px] font-semibold text-copper"
        >
          {isImage(file) ? "IMG" : "PDF"}
        </span>
      )}
      <span className="min-w-0">
        <span className="block truncate text-sm font-semibold text-ink" title={file.name}>
          {file.name}
        </span>
        <span className="block text-xs text-ink/60">{formatBytes(file.size)}</span>
      </span>
      <button
        type="button"
        onClick={onRemove}
        disabled={disabled}
        aria-label={`Remove ${file.name}`}
        className="ml-1 flex h-7 w-7 flex-none items-center justify-center rounded-full text-ink/60 hover:bg-line hover:text-ink disabled:cursor-not-allowed disabled:opacity-60"
      >
        <span aria-hidden="true">×</span>
      </button>
    </div>
  );
}
