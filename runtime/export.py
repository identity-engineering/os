"""Deterministic export of one local SQLite identity space."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Union

from .context import ContextError, resolve_active_identity_row
from .database import Database, DatabaseError, canonical_json, database_path, sha256_text

EXPORT_FORMAT = "identity-engineering.identity-space"
EXPORT_FORMAT_VERSION = 1

TABLE_QUERIES: dict[str, tuple[str, tuple[Any, ...]]] = {
    "install": ("SELECT * FROM install WHERE install_id = ?", ()),
    "identity": ("SELECT * FROM identity WHERE identity_id = ?", ()),
    "privacy_defaults": ("SELECT * FROM privacy_defaults WHERE identity_id = ?", ()),
    "consent_grants": ("SELECT * FROM consent_grants WHERE identity_id = ?", ()),
    "quarantines": ("SELECT * FROM quarantines WHERE identity_id = ?", ()),
    "policy_events": ("SELECT * FROM policy_events WHERE identity_id = ?", ()),
    "metric_dimensions": ("SELECT * FROM metric_dimensions WHERE identity_id = ?", ()),
    "metric_pairs": ("SELECT * FROM metric_pairs WHERE identity_id = ?", ()),
    "registry_entries": ("SELECT * FROM registry_entries WHERE identity_id = ?", ()),
    "registry_entry_revisions": (
        """
        SELECT r.*, ? AS identity_id
        FROM registry_entry_revisions r
        WHERE json_extract(r.snapshot_json, '$.identity_id') = ?
        ORDER BY r.entry_id, r.revision
        """,
        (),
    ),
    "registry_dimension_values": (
        """
        SELECT v.*
        FROM registry_dimension_values v
        JOIN registry_entries e ON e.entry_id = v.entry_id
        WHERE e.identity_id = ?
        """,
        (),
    ),
    "registry_dimension_revisions": (
        """
        SELECT r.*, d.identity_id
        FROM registry_dimension_revisions r
        JOIN metric_dimensions d ON d.dimension_id = r.dimension_id
        WHERE d.identity_id = ?
        ORDER BY r.entry_id, r.dimension_id, r.revision
        """,
        (),
    ),
    "interaction_events": ("SELECT * FROM interaction_events WHERE install_id = ?", ()),
    "apply_receipts": (
        """
        SELECT r.*
        FROM apply_receipts r
        JOIN interaction_events e ON e.event_id = r.event_id
        WHERE e.install_id = ?
        """,
        (),
    ),
    "foreign_estimates": ("SELECT * FROM foreign_estimates WHERE identity_id = ?", ()),
    "estimate_requests": ("SELECT * FROM estimate_requests WHERE identity_id = ?", ()),
    "evidence_sources": ("SELECT * FROM evidence_sources WHERE identity_id = ?", ()),
    "stem_state": ("SELECT * FROM stem_state WHERE identity_id = ?", ()),
    "stem_revisions": ("SELECT * FROM stem_revisions WHERE identity_id = ?", ()),
    "workspace_items": ("SELECT * FROM workspace_items WHERE identity_id = ?", ()),
    "workspace_item_revisions": (
        """
        SELECT r.*, ? AS identity_id
        FROM workspace_item_revisions r
        WHERE json_extract(r.snapshot_json, '$.identity_id') = ?
        ORDER BY r.item_id, r.revision
        """,
        (),
    ),
    "geometry_receipts": ("SELECT * FROM geometry_receipts WHERE install_id = ?", ()),
    "geometry_receipt_sources": (
        """
        SELECT s.*
        FROM geometry_receipt_sources s
        JOIN geometry_receipts r ON r.receipt_id = s.receipt_id
        WHERE r.install_id = ?
        """,
        (),
    ),
    "mature_events": ("SELECT * FROM mature_events WHERE identity_id = ?", ()),
    "trajectory_entries": ("SELECT * FROM trajectory_entries WHERE identity_id = ?", ()),
}


def _normalise_numbers(value: Any) -> Any:
    if isinstance(value, float):
        return int(value) if value.is_integer() else value
    if isinstance(value, list):
        return [_normalise_numbers(item) for item in value]
    if isinstance(value, dict):
        return {key: _normalise_numbers(item) for key, item in value.items()}
    return value


def _decode_json_columns(row: dict[str, Any]) -> dict[str, Any]:
    decoded: dict[str, Any] = {}
    for key, value in row.items():
        if not key.endswith("_json"):
            decoded[key] = value
            continue
        output_key = key.removesuffix("_json")
        if value is None:
            decoded[output_key] = None
            continue
        try:
            decoded[output_key] = _normalise_numbers(json.loads(value))
        except (TypeError, json.JSONDecodeError) as exc:
            raise DatabaseError(f"invalid JSON in {key}") from exc
    return _normalise_numbers(decoded)


def _query_rows(conn, table: str, identity_id: str, install_id: str) -> list[dict[str, Any]]:
    query, _ = TABLE_QUERIES[table]
    if table in {"install", "interaction_events", "geometry_receipts", "geometry_receipt_sources", "apply_receipts"}:
        parameters = (install_id,)
    elif table in {"registry_entry_revisions", "workspace_item_revisions"}:
        parameters = (identity_id, identity_id)
    else:
        parameters = (identity_id,)
    rows = [_decode_json_columns(dict(row)) for row in conn.execute(query, parameters).fetchall()]
    rows.sort(key=canonical_json)
    return rows


def _payload_for_database(conn) -> dict[str, Any]:
    install = conn.execute("SELECT * FROM install LIMIT 1").fetchone()
    try:
        identity = resolve_active_identity_row(conn)
    except ContextError as exc:
        raise DatabaseError("database has no local install and identity") from exc
    if install is None:
        raise DatabaseError("database has no local install and identity")

    identity_id = str(identity["identity_id"])
    install_id = str(install["install_id"])
    tables = {
        table: _query_rows(conn, table, identity_id, install_id)
        for table in TABLE_QUERIES
    }
    return {
        "format": EXPORT_FORMAT,
        "format_version": EXPORT_FORMAT_VERSION,
        "open_core_schema_version": int(conn.execute("PRAGMA user_version").fetchone()[0]),
        "source": {
            "install_id": install_id,
            "identity_id": identity_id,
            "local_handle": identity["local_handle"],
        },
        "tables": tables,
    }


def export_identity_space(install_root: Union[str, Path]) -> dict[str, Any]:
    """Return a deterministic export envelope for the active identity space."""
    root = Path(install_root).expanduser().resolve()
    if not database_path(root).is_file():
        raise DatabaseError(f"No IE database under {root}")
    with Database(root) as database:
        payload = _payload_for_database(database.conn)
    payload_sha256 = sha256_text(canonical_json(payload))
    return {
        "format": EXPORT_FORMAT,
        "format_version": EXPORT_FORMAT_VERSION,
        "export_id": payload_sha256,
        "payload_sha256": payload_sha256,
        "payload": payload,
    }


def verify_identity_export(document: Any) -> dict[str, Any]:
    """Validate the shape and checksum of an identity-space export."""
    if not isinstance(document, dict):
        raise ValueError("identity export must be an object")
    if document.get("format") != EXPORT_FORMAT:
        raise ValueError("unsupported identity export format")
    if document.get("format_version") != EXPORT_FORMAT_VERSION:
        raise ValueError("unsupported identity export version")
    payload = document.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("identity export payload must be an object")
    expected = sha256_text(canonical_json(payload))
    if document.get("payload_sha256") != expected:
        raise ValueError("identity export checksum mismatch")
    if document.get("export_id") != expected:
        raise ValueError("identity export id mismatch")
    if payload.get("format") != EXPORT_FORMAT:
        raise ValueError("identity export payload format mismatch")
    source = payload.get("source")
    tables = payload.get("tables")
    if not isinstance(source, dict) or not isinstance(tables, dict):
        raise ValueError("identity export source and tables are required")
    for required in ("install_id", "identity_id", "local_handle"):
        if not isinstance(source.get(required), str) or not source[required]:
            raise ValueError(f"identity export source.{required} is required")
    for table, rows in tables.items():
        if table not in TABLE_QUERIES or not isinstance(rows, list):
            raise ValueError(f"invalid identity export table: {table}")
        if not all(isinstance(row, dict) for row in rows):
            raise ValueError(f"invalid rows in identity export table: {table}")
    return document


def write_identity_export(
    install_root: Union[str, Path],
    destination: Union[str, Path],
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Write a pretty-printed export without changing its canonical checksum."""
    destination_path = Path(destination).expanduser().resolve()
    if destination_path.exists() and not overwrite:
        raise DatabaseError(f"Export destination already exists: {destination_path}")
    document = export_identity_space(install_root)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    destination_path.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "destination": str(destination_path),
        "export_id": document["export_id"],
        "payload_sha256": document["payload_sha256"],
        "table_counts": {
            table: len(rows) for table, rows in document["payload"]["tables"].items()
        },
    }
