"""SQLite database lifecycle and the initial DB-only V1 schema."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional, Union
from uuid import uuid4

DB_DIR_NAME = ".ie"
DB_FILENAME = "ie.sqlite3"
SCHEMA_VERSION = 5


class DatabaseError(RuntimeError):
    """Raised when a local IE database cannot be opened or initialized."""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    """Serialize JSON fields deterministically for storage and hashing."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def database_path(install_root: Union[str, Path]) -> Path:
    return Path(install_root).expanduser().resolve() / DB_DIR_NAME / DB_FILENAME


def _resolve_database_path(path: Union[str, Path]) -> Path:
    candidate = Path(path).expanduser()
    if candidate.name == DB_FILENAME or candidate.suffix in {".db", ".sqlite", ".sqlite3"}:
        return candidate.resolve()
    return database_path(candidate)
