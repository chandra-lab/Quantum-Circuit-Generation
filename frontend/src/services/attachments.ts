export const ACCEPTED_TYPES = ["image/png", "image/jpeg", "image/webp", "application/pdf"] as const;

export const ACCEPT_ATTRIBUTE = [...ACCEPTED_TYPES, ".png", ".jpg", ".jpeg", ".webp", ".pdf"].join(",");

export const DEFAULT_MAX_UPLOAD_MB = 10;

const TYPES_BY_EXTENSION: Record<string, string> = {
  png: "image/png",
  jpg: "image/jpeg",
  jpeg: "image/jpeg",
  webp: "image/webp",
  pdf: "application/pdf",
};

/** Some platforms leave File.type empty, so fall back to the extension. The server checks the bytes. */
export function attachmentType(file: File): string {
  if (file.type) {
    return file.type;
  }
  const extension = file.name.split(".").pop()?.toLowerCase() ?? "";
  return TYPES_BY_EXTENSION[extension] ?? "";
}

export function isImage(file: File): boolean {
  return attachmentType(file).startsWith("image/");
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  if (bytes < 1024 * 1024) {
    return `${(bytes / 1024).toFixed(0)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/** Returns a message when the file cannot be attached, or null when it can. */
export function validateAttachment(file: File, maxUploadMb: number): string | null {
  if (!(ACCEPTED_TYPES as readonly string[]).includes(attachmentType(file))) {
    return `${file.name} is not a PNG, JPEG, WebP, or PDF file.`;
  }
  if (file.size === 0) {
    return `${file.name} is empty.`;
  }
  if (file.size > maxUploadMb * 1024 * 1024) {
    return `${file.name} is ${formatBytes(file.size)}. The limit is ${maxUploadMb} MB.`;
  }
  return null;
}
