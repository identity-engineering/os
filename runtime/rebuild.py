"""Rebuild SQLite projections from the append-only V1 history."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Union

from .database import Database, DatabaseError, canonical_json, database_path, utcnow

REGISTRY_JSON_FIELDS = {
    "recognition": "recognition_json",
    "relation": "relation_json",
    "effect_on_me": "effect_on_me_json",
    "perceived_ownership": "perceived_ownership_json",
    "privacy": "privacy_json",
    "tags": "tags_json",
}
REGISTRY_SCALAR_FIELDS = (
    "preferred_name",
    "substrate",
    "description",
    "first_noticed",
    "last_interaction",
    "interaction_count",
    "interaction_depth",
    "my_mass_estimate",
    "mass_confidence",
    "estimate_updated_at",
    "estimate_as_of_peer_mature_at",
    "peer_last_mature_at",
    "peer_last_mature_seen_at",
    "notes",
    "source",
    "revision",
    "created_at",
    "updated_at",
)
REGISTRY_COLUMNS = (
    "entry_id",
    "identity_id",
    "peer_handle",
    *REGISTRY_SCALAR_FIELDS,
    "recognition_json",
    "relation_json",
    "effect_on_me_json",
    "perceived_ownership_json",
    "privacy_json",
    "tags_json",
)


def _decode_json(raw: Any, default: Any) -> Any:
    if raw is None or raw == "":
        return default
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise DatabaseError("append-only history contains invalid JSON") from exc


def _latest(rows, key_fields: tuple[str, ...]) -> dict[tuple[Any, ...], Any]:
    latest: dict[tuple[Any, ...], Any] = {}
    for row in rows:
        key = tuple(row[field] for field in key_fields)
        current = latest.get(key)
        if current is None or int(row["revision"]) > int(current["revision"]):
            latest[key] = row
    return latest


def _rebuild_foreign_estimates(conn, *, identity_id: str, install_id: str) -> tuple[int, str | None]:
    records: dict[str, dict[str, Any]] = {}
    last_signal_at: str | None = None
    rows = conn.execute(
        """
        SELECT e.event_id, e.from_handle, e.signal_timestamp, e.received_at,
               e.canonical_payload_json, r.receipt_id, r.applied_fields_json,
               r.quarantine
        FROM interaction_events e
        JOIN apply_receipts r ON r.event_id = e.event_id
        WHERE e.install_id = ?
        ORDER BY e.received_at, e.event_id
        """,
        (install_id,),
    ).fetchall()
    for row in rows:
        fields = _decode_json(row["applied_fields_json"], [])
        if not isinstance(fields, list):
            raise DatabaseError("apply receipt history contains invalid applied_fields_json")
        if not fields:
            continue
        payload = _decode_json(row["canonical_payload_json"], {})
        if not isinstance(payload, dict):
            raise DatabaseError("interaction event history contains an invalid payload")
        sender = row["from_handle"]
        signal_time = row["signal_timestamp"] or row["received_at"]
        record = records.setdefault(
            sender,
            {
                "identity_id": identity_id,
                "sender_handle": sender,
                "sender_substrate": None,
                "first_signal_at": signal_time,
                "last_signal_at": signal_time,
                "signal_count": 0,
                "accumulated_depth": 0.0,
                "last_depth_delta": 0.0,
                "existence_confirmed": 0,
                "coarse_mass_estimate": None,
                "mass_confidence": None,
                "mass_estimate_at": None,
                "dimensions_delta_json": None,
                "relation_pull": None,
                "sender_emergent_mass": None,
                "sender_emergent_mass_at": None,
                "sender_last_mature_at": None,
                "sender_last_mature_seen_at": None,
                "last_receipt_id": None,
                "quarantine": 0,
                "notes": None,
            },
        )
        record["last_signal_at"] = signal_time
        record["signal_count"] += 1
        record["quarantine"] = int(row["quarantine"])
        record["last_receipt_id"] = row["receipt_id"]
        last_signal_at = row["received_at"]
        if "existence" in fields:
            record["existence_confirmed"] = 1
        if "interaction_depth_delta" in fields:
            delta = float(payload.get("interaction_depth_delta") or 0.0)
            record["last_depth_delta"] = delta
            record["accumulated_depth"] += delta
        if "sender_emergent_mass" in fields:
            record["sender_emergent_mass"] = payload.get("sender_emergent_mass")
            record["sender_emergent_mass_at"] = signal_time
        if "sender_last_mature_at" in fields:
            record["sender_last_mature_at"] = payload.get("sender_last_mature_at")
            record["sender_last_mature_seen_at"] = row["received_at"]
        if "coarse_mass_estimate" in fields:
            record["coarse_mass_estimate"] = payload.get("coarse_mass_estimate")
            record["mass_estimate_at"] = signal_time
        if "mass_confidence" in fields:
            record["mass_confidence"] = payload.get("mass_confidence")
        if "dimensions_delta" in fields:
            record["dimensions_delta_json"] = canonical_json(payload.get("dimensions_delta"))
        if "relation_pull" in fields:
            record["relation_pull"] = payload.get("relation_pull")

    conn.execute("DELETE FROM foreign_estimates WHERE identity_id = ?", (identity_id,))
    columns = (
        "identity_id",
        "sender_handle",
        "sender_substrate",
        "first_signal_at",
        "last_signal_at",
        "signal_count",
        "accumulated_depth",
        "last_depth_delta",
        "existence_confirmed",
        "coarse_mass_estimate",
        "mass_confidence",
        "mass_estimate_at",
        "dimensions_delta_json",
        "relation_pull",
        "sender_emergent_mass",
        "sender_emergent_mass_at",
        "sender_last_mature_at",
        "sender_last_mature_seen_at",
        "last_receipt_id",
        "quarantine",
        "notes",
    )
    for record in records.values():
        conn.execute(
            f"INSERT INTO foreign_estimates({', '.join(columns)}) "
            f"VALUES ({', '.join('?' for _ in columns)})",
            tuple(record[column] for column in columns),
        )
    return len(records), last_signal_at


def _registry_values(snapshot: dict[str, Any], *, identity_id: str) -> dict[str, Any]:
    values: dict[str, Any] = {
        "entry_id": snapshot["entry_id"],
        "identity_id": identity_id,
        "peer_handle": snapshot["peer_handle"],
    }
    values.update({field: snapshot.get(field) for field in REGISTRY_SCALAR_FIELDS})
    for logical_name, column_name in REGISTRY_JSON_FIELDS.items():
        raw = snapshot.get(column_name)
        if raw is not None:
            values[column_name] = raw if isinstance(raw, str) else canonical_json(raw)
            continue
        default = [] if logical_name == "tags" else {}
        values[column_name] = canonical_json(snapshot.get(logical_name, default))
    return values


def _rebuild_registry(conn, *, identity_id: str) -> tuple[int, int]:
    rows = conn.execute(
        """
        SELECT r.*
        FROM registry_entry_revisions r
        JOIN registry_entries e ON e.entry_id = r.entry_id
        WHERE e.identity_id = ?
        ORDER BY r.entry_id, r.revision
        """,
        (identity_id,),
    ).fetchall()
    latest = _latest(rows, ("entry_id",))
    if latest:
        entry_ids = [key[0] for key in latest]
        placeholders = ", ".join("?" for _ in entry_ids)
        conn.execute(
            f"""
            DELETE FROM registry_entries
            WHERE identity_id = ?
              AND entry_id NOT IN ({placeholders})
            """,
            (identity_id, *entry_ids),
        )
    else:
        conn.execute("DELETE FROM registry_entries WHERE identity_id = ?", (identity_id,))

    for revision in latest.values():
        snapshot = _decode_json(revision["snapshot_json"], {})
        if not isinstance(snapshot, dict):
            raise DatabaseError("registry revision history contains an invalid snapshot")
        values = _registry_values(snapshot, identity_id=identity_id)
        existing = conn.execute(
            "SELECT 1 FROM registry_entries WHERE entry_id = ?",
            (values["entry_id"],),
        ).fetchone()
        if existing is None:
            conn.execute(
                f"INSERT INTO registry_entries({', '.join(REGISTRY_COLUMNS)}) "
                f"VALUES ({', '.join('?' for _ in REGISTRY_COLUMNS)})",
                tuple(values[column] for column in REGISTRY_COLUMNS),
            )
        else:
            updates = [column for column in REGISTRY_COLUMNS if column not in {"entry_id", "identity_id", "peer_handle"}]
            conn.execute(
                f"UPDATE registry_entries SET {', '.join(f'{column} = ?' for column in updates)} "
                "WHERE entry_id = ? AND identity_id = ?",
                tuple(values[column] for column in updates)
                + (values["entry_id"], identity_id),
            )

    entry_ids = [revision["entry_id"] for revision in latest.values()]
    if entry_ids:
        placeholders = ", ".join("?" for _ in entry_ids)
        conn.execute(
            f"DELETE FROM registry_dimension_values WHERE entry_id IN ({placeholders})",
            tuple(entry_ids),
        )
    dimension_rows = conn.execute(
        """
        SELECT r.*
        FROM registry_dimension_revisions r
        JOIN registry_entries e ON e.entry_id = r.entry_id
        WHERE e.identity_id = ?
        ORDER BY r.entry_id, r.dimension_id, r.revision
        """,
        (identity_id,),
    ).fetchall()
    dimensions = _latest(dimension_rows, ("entry_id", "dimension_id"))
    for revision in dimensions.values():
        snapshot = _decode_json(revision["snapshot_json"], {})
        if not isinstance(snapshot, dict):
            raise DatabaseError("registry dimension history contains an invalid snapshot")
        conn.execute(
            """
            INSERT INTO registry_dimension_values(
                entry_id, dimension_id, value, confidence, source, note,
                observed_at, revision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                revision["entry_id"],
                revision["dimension_id"],
                snapshot["value"],
                snapshot["confidence"],
                snapshot["source"],
                snapshot.get("note", ""),
                snapshot["observed_at"],
                revision["revision"],
            ),
        )
    return len(latest), len(dimensions)


def _rebuild_stem(conn, *, identity_id: str) -> int:
    row = conn.execute(
        """
        SELECT * FROM stem_revisions
        WHERE identity_id = ?
        ORDER BY revision DESC LIMIT 1
        """,
        (identity_id,),
    ).fetchone()
    if row is None:
        return 0
    snapshot = _decode_json(row["snapshot_json"], {})
    if not isinstance(snapshot, dict):
        raise DatabaseError("stem revision history contains an invalid snapshot")
    conn.execute(
        """
        UPDATE stem_state
        SET revision = ?, state_differential_json = ?, vision_gradient_json = ?,
            coherence_json = ?, substance_json = ?, updated_at = ?, last_mature_id = ?
        WHERE identity_id = ?
        """,
        (
            row["revision"],
            canonical_json(snapshot.get("state_differential", {})),
            canonical_json(snapshot.get("vision_gradient", {})),
            canonical_json(snapshot.get("coherence", {})),
            canonical_json(snapshot.get("substance", {})),
            snapshot.get("updated_at") or row["created_at"],
            snapshot.get("last_mature_id"),
            identity_id,
        ),
    )
    return 1


def _rebuild_workspace(conn, *, identity_id: str) -> int:
    rows = conn.execute(
        """
        SELECT r.*
        FROM workspace_item_revisions r
        JOIN workspace_items w ON w.item_id = r.item_id
        WHERE w.identity_id = ?
        ORDER BY r.item_id, r.revision
        """,
        (identity_id,),
    ).fetchall()
    latest = _latest(rows, ("item_id",))
    if latest:
        item_ids = [key[0] for key in latest]
        placeholders = ", ".join("?" for _ in item_ids)
        conn.execute(
            f"""
            DELETE FROM workspace_items
            WHERE identity_id = ?
              AND item_id NOT IN ({placeholders})
            """,
            (identity_id, *item_ids),
        )
    else:
        conn.execute("DELETE FROM workspace_items WHERE identity_id = ?", (identity_id,))
    for revision in latest.values():
        snapshot = _decode_json(revision["snapshot_json"], {})
        if not isinstance(snapshot, dict):
            raise DatabaseError("workspace revision history contains an invalid snapshot")
        tags = snapshot.get("tags_json", snapshot.get("tags", []))
        tags_json = tags if isinstance(tags, str) else canonical_json(tags)
        fields = {
            "item_id": snapshot["item_id"],
            "identity_id": identity_id,
            "kind": snapshot["kind"],
            "title": snapshot["title"],
            "content": snapshot["content"],
            "status": snapshot["status"],
            "priority": snapshot.get("priority"),
            "due_at": snapshot.get("due_at"),
            "tags_json": tags_json,
            "source_id": snapshot.get("source_id"),
            "revision": snapshot["revision"],
            "created_at": snapshot["created_at"],
            "updated_at": snapshot["updated_at"],
        }
        existing = conn.execute(
            "SELECT 1 FROM workspace_items WHERE item_id = ?",
            (fields["item_id"],),
        ).fetchone()
        columns = tuple(fields)
        if existing is None:
            conn.execute(
                f"INSERT INTO workspace_items({', '.join(columns)}) "
                f"VALUES ({', '.join('?' for _ in columns)})",
                tuple(fields[column] for column in columns),
            )
        else:
            updates = [column for column in columns if column not in {"item_id", "identity_id", "created_at"}]
            conn.execute(
                f"UPDATE workspace_items SET {', '.join(f'{column} = ?' for column in updates)} "
                "WHERE item_id = ? AND identity_id = ?",
                tuple(fields[column] for column in updates)
                + (fields["item_id"], identity_id),
            )
    return len(latest)


def rebuild_projections(install_root: Union[str, Path]) -> dict[str, Any]:
    """Restore current projections from canonical events and revision snapshots."""
    root = Path(install_root).expanduser().resolve()
    if not database_path(root).is_file():
        raise DatabaseError(f"No IE database under {root}")
    rebuilt_at = utcnow()
    with Database(root) as database:
        with database.transaction() as conn:
            identity = conn.execute(
                "SELECT identity_id, install_id FROM identity LIMIT 1"
            ).fetchone()
            if identity is None:
                raise DatabaseError("database has no local identity")
            foreign_count, last_signal_at = _rebuild_foreign_estimates(
                conn,
                identity_id=identity["identity_id"],
                install_id=identity["install_id"],
            )
            registry_count, dimension_count = _rebuild_registry(
                conn,
                identity_id=identity["identity_id"],
            )
            stem_count = _rebuild_stem(conn, identity_id=identity["identity_id"])
            workspace_count = _rebuild_workspace(conn, identity_id=identity["identity_id"])
            last_mature_at = conn.execute(
                "SELECT MAX(created_at) FROM mature_events WHERE identity_id = ?",
                (identity["identity_id"],),
            ).fetchone()[0]
            conn.execute(
                """
                UPDATE identity
                SET last_signal_at = ?, last_mature_at = ?, updated_at = ?
                WHERE identity_id = ?
                """,
                (last_signal_at, last_mature_at, rebuilt_at, identity["identity_id"]),
            )
            conn.execute(
                "UPDATE install SET updated_at = ? WHERE install_id = ?",
                (rebuilt_at, identity["install_id"]),
            )
    return {
        "root": str(root),
        "rebuilt_at": rebuilt_at,
        "foreign_estimates": foreign_count,
        "registry_entries": registry_count,
        "registry_dimensions": dimension_count,
        "stem": stem_count,
        "workspace_items": workspace_count,
        "last_signal_at": last_signal_at,
        "last_mature_at": last_mature_at,
    }
