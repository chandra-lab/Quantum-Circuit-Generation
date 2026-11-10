"""Keep secrets out of logs."""

from __future__ import annotations

import logging

_SECRET = ""


def redact(text: str, secret: str | None) -> str:
    if not text or not secret:
        return text
    return text.replace(secret, "[REDACTED]")


class RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        secret = _SECRET
        if not secret:
            return True
        try:
            message = record.getMessage()
        except Exception:
            return True
        if secret in message:
            record.msg = message.replace(secret, "[REDACTED]")
            record.args = ()
        return True


def install_redaction(secret: str) -> None:
    """Install a handler filter that strips the API key from log lines."""

    global _SECRET
    _SECRET = secret or ""
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=logging.INFO)
    redactor = RedactFilter()
    for handler in root.handlers:
        if not any(isinstance(existing, RedactFilter) for existing in handler.filters):
            handler.addFilter(redactor)
