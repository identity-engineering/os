"""ie registry list|get for the SQLite-first local Registry."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from runtime.database import Database, database_path


JSON_COLUMNS = {
    "recognition_json": "recognition",
    "relation_json": "relation",
    "effect_on_me_json": "effect_on_me",
    "perceived_ownership_json": "perceived_ownership",
    "privacy_json": "privacy",
    "tags_json": "tags",
}


def _decode_entry(row: Any) -> dict[str, Any]:
    data = dict(row)
    data["local_handle"] = data.pop("peer_handle")
    for column, key in JSON_COLUMNS.items():
        raw = data.pop(column, None)
        if raw is None:
            continue
        try:
            data[key] = json.loads(raw)
        except (TypeError, json.JSONDecodeError):
            data[key] = raw
    return data


def list_peers(root: Path) -> list[str]:
    db_path = database_path(root)
    if not db_path.is_file():
        return []
    with Database(db_path) as database:
        return [
            row[0]
            for row in database.conn.execute(
                "SELECT peer_handle FROM registry_entries ORDER BY peer_handle"
            ).fetchall()
        ]


def get_peer(root: Path, handle: str) -> Optional[dict[str, Any]]:
    db_path = database_path(root)
    if not db_path.is_file():
        return None
    with Database(db_path) as database:
        row = database.conn.execute(
            "SELECT * FROM registry_entries WHERE peer_handle = ?",
            (handle,),
        ).fetchone()
    return _decode_entry(row) if row is not None else None
