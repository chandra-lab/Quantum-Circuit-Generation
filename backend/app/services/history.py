"""Optional run history. Failures here never block generation or simulation."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

logger = logging.getLogger(__name__)


@dataclass
class RunRecord:
    kind: str
    source: str
    prompt: str | None
    circuit_name: str | None
    num_qubits: int | None
    valid: bool


class RunHistoryRepository(Protocol):
    def record(self, entry: RunRecord) -> None: ...

    def recent(self, limit: int = 20) -> list[dict[str, object]]: ...


class NullRunHistory:
    def record(self, entry: RunRecord) -> None:
        return None

    def recent(self, limit: int = 20) -> list[dict[str, object]]:
        return []


class SqliteRunHistory:
    def __init__(self, path: str) -> None:
        self.path = path
        if path != ":memory:":
            Path(path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS run_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    source TEXT NOT NULL,
                    prompt TEXT,
                    circuit_name TEXT,
                    num_qubits INTEGER,
                    valid INTEGER NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def record(self, entry: RunRecord) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO run_history (
                    created_at, kind, source, prompt, circuit_name, num_qubits, valid
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    datetime.now(timezone.utc).isoformat(),
                    entry.kind,
                    entry.source,
                    entry.prompt,
                    entry.circuit_name,
                    entry.num_qubits,
                    1 if entry.valid else 0,
                ),
            )

    def recent(self, limit: int = 20) -> list[dict[str, object]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT created_at, kind, source, prompt, circuit_name, num_qubits, valid
                FROM run_history
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [
            {
                "created_at": row[0],
                "kind": row[1],
                "source": row[2],
                "prompt": row[3],
                "circuit_name": row[4],
                "num_qubits": row[5],
                "valid": bool(row[6]),
            }
            for row in rows
        ]


def build_history(enabled: bool, path: str) -> RunHistoryRepository:
    if not enabled:
        return NullRunHistory()
    try:
        return SqliteRunHistory(path)
    except Exception:
        logger.warning("run history disabled because the database could not be opened")
        return NullRunHistory()


def safe_record(repository: RunHistoryRepository, entry: RunRecord) -> None:
    try:
        repository.record(entry)
    except Exception:
        logger.warning("run history write failed")
