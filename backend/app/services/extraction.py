"""Check uploads and read a quantum question out of an image or PDF.

Uploads stay in memory. Nothing here writes to disk.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass

from app.core.config import Settings
from app.core.errors import ExtractionError, FileTooLargeError, UnsupportedFileTypeError
from app.services.llm.base import ImageInput

MEDIA_TYPES: dict[str, str] = {
    "png": "image/png",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "pdf": "application/pdf",
}
DECLARED_TYPES: dict[str, str] = {
    "image/png": "png",
    "image/jpeg": "jpeg",
    "image/jpg": "jpeg",
    "image/pjpeg": "jpeg",
    "image/webp": "webp",
    "application/pdf": "pdf",
}

# A PDF page with fewer letters and digits than this is treated as a scan.
MIN_TEXT_CHARS = 20
# Long side, in pixels, of a scanned page rendered for the vision model.
RENDER_LONG_SIDE = 1600

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


@dataclass(frozen=True)
class Upload:
    filename: str
    kind: str
    data: bytes

    @property
    def media_type(self) -> str:
        return MEDIA_TYPES[self.kind]

    @property
    def is_pdf(self) -> bool:
        return self.kind == "pdf"


@dataclass(frozen=True)
class PdfText:
    text: str
    pages_read: int
    total_pages: int


def sniff_kind(data: bytes) -> str | None:
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    # The PDF spec lets the header start anywhere in the first 1024 bytes.
    if b"%PDF-" in data[:1024]:
        return "pdf"
    return None


def clean_filename(name: str | None) -> str:
    base = (name or "upload").replace("\\", "/").rsplit("/", 1)[-1]
    base = _CONTROL_CHARS.sub("", base).strip()
    return base[:200] or "upload"


def check_upload(
    filename: str | None,
    declared_type: str | None,
    data: bytes,
    settings: Settings,
) -> Upload:
    if len(data) > settings.max_upload_bytes:
        raise FileTooLargeError(settings.max_upload_mb)
    declared = (declared_type or "").split(";", 1)[0].strip().lower()
    declared_kind = DECLARED_TYPES.get(declared)
    if declared_kind is None:
        label = declared or "unknown"
        raise UnsupportedFileTypeError(
            f"File type {label} is not supported. Upload a PNG, JPEG, WebP, or PDF file."
        )
    if not data:
        raise ExtractionError("The uploaded file is empty.", code="empty_file")
    actual = sniff_kind(data)
    if actual is None:
        raise UnsupportedFileTypeError(
            "The file contents are not a PNG, JPEG, WebP, or PDF file."
        )
    if actual != declared_kind:
        raise UnsupportedFileTypeError(
            f"The file was sent as {declared} but its contents are {MEDIA_TYPES[actual]}."
        )
    return Upload(filename=clean_filename(filename), kind=actual, data=data)


def normalize_text(text: str) -> str:
    text = _CONTROL_CHARS.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))
    lines = [re.sub(r"[ \t\u00a0]+", " ", line).strip() for line in text.split("\n")]
    joined = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", joined).strip()


def has_meaningful_text(text: str) -> bool:
    return sum(1 for char in text if char.isalnum()) >= MIN_TEXT_CHARS


def cap_text(text: str, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    return text[:max_chars].rstrip(), True


def extract_pdf_text(data: bytes, *, max_pages: int) -> PdfText:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError

    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted and not reader.decrypt(""):
            raise ExtractionError(
                "The PDF is password protected. Upload an unlocked copy.",
                code="unreadable_file",
            )
        total = len(reader.pages)
        parts: list[str] = []
        for page in reader.pages[:max_pages]:
            parts.append(page.extract_text() or "")
    except ExtractionError:
        raise
    except (PdfReadError, ValueError, KeyError, TypeError, OSError, NotImplementedError) as exc:
        raise ExtractionError(
            "The PDF could not be read. It may be damaged or use an unsupported feature.",
            code="unreadable_file",
        ) from exc
    if total == 0:
        raise ExtractionError("The PDF has no pages.", code="extraction_empty")
    return PdfText(
        text=normalize_text("\n\n".join(parts)),
        pages_read=min(total, max_pages),
        total_pages=total,
    )


def render_pdf_pages(data: bytes, *, max_pages: int) -> list[ImageInput]:
    """Render the first pages of a scanned PDF to JPEG for the vision model."""
    import pypdfium2 as pdfium

    images: list[ImageInput] = []
    try:
        document = pdfium.PdfDocument(data)
    except pdfium.PdfiumError as exc:
        raise ExtractionError(
            "The PDF could not be rendered for image reading.",
            code="unreadable_file",
        ) from exc
    try:
        for index in range(min(len(document), max_pages)):
            page = document[index]
            try:
                width, height = page.get_size()
                scale = min(3.0, RENDER_LONG_SIDE / max(width, height, 1.0))
                bitmap = page.render(scale=scale)
                picture = bitmap.to_pil().convert("RGB")
                buffer = io.BytesIO()
                picture.save(buffer, format="JPEG", quality=85)
                images.append(ImageInput(media_type="image/jpeg", data=buffer.getvalue()))
            finally:
                page.close()
    finally:
        document.close()
    if not images:
        raise ExtractionError("The PDF has no pages.", code="extraction_empty")
    return images
