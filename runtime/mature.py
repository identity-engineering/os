"""Transactional Mature learning for the SQLite-first local runtime."""

from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union
from uuid import uuid4

from .database import Database, canonical_json, database_path, utcnow
from .geometry import GeometryReceipt, create_self_probe
from .sqlite_store import SQLiteStore


WORKSPACE_KINDS = {
    "observation",
    "hypothesis",
    "decision",
    "commitment",
    "question",
    "goal",
    "note",
}
WORKSPACE_OPERATIONS = {"create", "update", "complete", "archive"}
REGISTRY_JSON_FIELDS = {
    "recognition": "recognition_json",
    "relation": "relation_json",
    "effect_on_me": "effect_on_me_json",
    "perceived_ownership": "perceived_ownership_json",
    "privacy": "privacy_json",
    "tags": "tags_json",
}
REGISTRY_SCALAR_FIELDS = {
    "preferred_name",
    "substrate",
    "description",
    "last_interaction",
    "interaction_count",
    "interaction_depth",
    "my_mass_estimate",
    "mass_confidence",
    "estimate_as_of_peer_mature_at",
    "peer_last_mature_at",
    "peer_last_mature_seen_at",
    "notes",
    "source",
}


class MatureError(ValueError):
    """Raised when a Mature change set cannot be committed."""


class MatureResult(dict):
    """Stable result payload for CLI, agents, and tests."""

    def __init__(self, **values: Any) -> None:
        super().__init__(values)

    def to_dict(self) -> dict[str, Any]:
        return dict(self)


def _finite(value: Any, label: str, *, minimum: Optional[float] = None, maximum: Optional[float] = None) -> float:
    if isinstance(value, bool):
        raise MatureError(f"{label} must be a finite number")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise MatureError(f"{label} must be a finite number") from exc
    if not math.isfinite(number):
        raise MatureError(f"{label} must be a finite number")
    if minimum is not None and number < minimum:
        raise MatureError(f"{label} must be >= {minimum}")
    if maximum is not None and number > maximum:
        raise MatureError(f"{label} must be <= {maximum}")
    return number


def _json_object(raw: Optional[str], label: str) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MatureError(f"stored {label} is not valid JSON") from exc
    if not isinstance(value, dict):
        raise MatureError(f"stored {label} must be an object")
    return value


def _normalise_list(value: Any, label: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if isinstance(value, dict):
        return [dict(value)]
    if not isinstance(value, (list, tuple)):
        raise MatureError(f"{label} must be an object or list of objects")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise MatureError(f"{label}[{index}] must be an object")
        result.append(dict(item))
    return result


def _normalise_stem(raw: Optional[dict[str, Any]]) -> Optional[dict[str, str]]:
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise MatureError("stem_differential must be an object")
    result: dict[str, str] = {}
    for field in ("state_delta_summary", "vision_gradient_shift", "coherence_note"):
        if field not in raw:
            continue
        value = raw[field]
        if not isinstance(value, str):
            raise MatureError(f"stem_differential.{field} must be a string")
        if value.strip():
            result[field] = value.strip()
    return result or None


def _normalise_workspace(raw: Any) -> list[dict[str, Any]]:
    changes = _normalise_list(raw, "workspace_changes")
    result: list[dict[str, Any]] = []
    for index, change in enumerate(changes):
        operation = str(change.get("operation", "create")).strip().lower()
        if operation not in WORKSPACE_OPERATIONS:
            raise MatureError(f"workspace_changes[{index}].operation is invalid")
        if operation == "create" and not change.get("item_id"):
            change.pop("item_id", None)
        if "kind" in change and change["kind"] not in WORKSPACE_KINDS:
            raise MatureError(f"workspace_changes[{index}].kind is invalid")
        if "tags" in change:
            if not isinstance(change["tags"], list) or not all(
                isinstance(tag, str) and tag.strip() for tag in change["tags"]
            ):
                raise MatureError(f"workspace_changes[{index}].tags must be a list of strings")
            change["tags"] = [tag.strip() for tag in change["tags"]]
        result.append(change)
    return result


def _normalise_dimensions(raw: Any, label: str) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if isinstance(raw, dict):
        converted: list[dict[str, Any]] = []
        for name, spec in raw.items():
            if isinstance(spec, dict):
                item = dict(spec)
            else:
                item = {"value": spec}
            item["name"] = name
            converted.append(item)
        raw = converted
    if not isinstance(raw, (list, tuple)):
        raise MatureError(f"{label} must be a list or object")
    result: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise MatureError(f"{label}[{index}] must be an object")
        name = str(item.get("name", "")).strip()
        if not name:
            raise MatureError(f"{label}[{index}].name is required")
        if "value" not in item:
            raise MatureError(f"{label}[{index}].value is required")
        if "confidence" not in item:
            raise MatureError(f"{label}[{index}].confidence is required")
        value = _finite(item["value"], f"{label}[{index}].value")
        confidence = _finite(
            item["confidence"],
            f"{label}[{index}].confidence",
            minimum=0.0,
            maximum=1.0,
        )
        result.append(
            {
                "name": name,
                "value": value,
                "confidence": confidence,
                "source": str(item.get("source", "mature")),
                "note": str(item.get("note", "")),
                "observed_at": str(item.get("observed_at", "")),
            }
        )
    return result


def _normalise_registry(raw: Any) -> list[dict[str, Any]]:
    changes = _normalise_list(raw, "registry_changes")
    result: list[dict[str, Any]] = []
    for index, change in enumerate(changes):
        handle = str(
            change.get("peer_handle")
            or change.get("handle")
            or change.get("local_handle")
            or ""
        ).strip()
        if not handle:
            raise MatureError(f"registry_changes[{index}].peer_handle is required")
        change["peer_handle"] = handle
        if "my_mass_estimate" in change and change["my_mass_estimate"] is not None:
            change["my_mass_estimate"] = _finite(
                change["my_mass_estimate"],
                f"registry_changes[{index}].my_mass_estimate",
                minimum=0.0,
                maximum=100.0,
            )
            if "mass_confidence" not in change:
                raise MatureError(
                    f"registry_changes[{index}].mass_confidence is required when estimate changes"
                )
        if "mass_confidence" in change and change["mass_confidence"] is not None:
            change["mass_confidence"] = _finite(
                change["mass_confidence"],
                f"registry_changes[{index}].mass_confidence",
                minimum=0.0,
                maximum=1.0,
            )
        for field_name, column_name in REGISTRY_JSON_FIELDS.items():
            if field_name not in change:
                continue
            if field_name == "tags":
                if not isinstance(change[field_name], list) or not all(
                    isinstance(tag, str) for tag in change[field_name]
                ):
                    raise MatureError(f"registry_changes[{index}].tags must be a list")
            elif not isinstance(change[field_name], dict):
                raise MatureError(f"registry_changes[{index}].{field_name} must be an object")
        unsupported = set(change) - (
            {"peer_handle", "dimensions"}
            | REGISTRY_JSON_FIELDS.keys()
            | REGISTRY_SCALAR_FIELDS
        )
        if unsupported:
            names = ", ".join(sorted(unsupported))
            raise MatureError(f"registry_changes[{index}] has unsupported fields: {names}")
        change["dimensions"] = _normalise_dimensions(
            change.get("dimensions"), f"registry_changes[{index}].dimensions"
        )
        result.append(change)
    return result


def _prepare_sources(
    root: Path,
    source_refs: list[str],
    *,
    capture_snapshots: bool,
) -> list[dict[str, Any]]:
    if not source_refs:
        raise MatureError("Mature requires at least one source reference")
    prepared: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_ref in source_refs:
        if not isinstance(raw_ref, str) or not raw_ref.strip():
            raise MatureError("source references must be non-empty strings")
        candidate = Path(raw_ref).expanduser()
        if not candidate.is_absolute():
            candidate = root / candidate
        candidate = candidate.resolve()
        try:
            relative = candidate.relative_to(root)
        except ValueError as exc:
            raise MatureError("Mature sources must stay inside the install root") from exc
        ref = relative.as_posix()
        if ref in seen:
            continue
        seen.add(ref)
        if not candidate.is_file():
            raise MatureError(f"Mature source does not exist or is not a file: {raw_ref}")
        content = candidate.read_bytes()
        stat = candidate.stat()
        snapshot: Optional[str] = None
        if capture_snapshots:
            try:
                snapshot = content.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise MatureError(f"Mature snapshot is not UTF-8 text: {raw_ref}") from exc
        prepared.append(
            {
                "source_ref": ref,
                "root_relative_path": ref,
                "byte_size": len(content),
                "observed_mtime": datetime.fromtimestamp(
                    stat.st_mtime, timezone.utc
                ).isoformat(),
                "sha256": hashlib.sha256(content).hexdigest(),
                "snapshot_text": snapshot,
            }
        )
    return prepared


def _insert_evidence_sources(
    conn,
    identity_id: str,
    prepared: list[dict[str, Any]],
    *,
    captured_at: str,
) -> dict[str, str]:
    source_ids: dict[str, str] = {}
    for source in prepared:
        conn.execute(
            """
            INSERT OR IGNORE INTO evidence_sources(
                source_id, identity_id, source_kind, source_ref, root_relative_path,
                byte_size, observed_mtime, sha256, snapshot_text, captured_at, created_at
            ) VALUES (?, ?, 'file', ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid4()),
                identity_id,
                source["source_ref"],
                source["root_relative_path"],
                source["byte_size"],
                source["observed_mtime"],
                source["sha256"],
                source["snapshot_text"],
                captured_at if source["snapshot_text"] is not None else None,
                captured_at,
            ),
        )
        row = conn.execute(
            """
            SELECT source_id FROM evidence_sources
            WHERE identity_id = ? AND source_kind = 'file'
              AND source_ref = ? AND sha256 = ?
            """,
            (identity_id, source["source_ref"], source["sha256"]),
        ).fetchone()
        if row is None:
            raise MatureError(f"could not persist evidence source: {source['source_ref']}")
        source_ids[source["source_ref"]] = row[0]
    return source_ids


def _stem_snapshot(row) -> dict[str, Any]:
    return {
        "identity_id": row["identity_id"],
        "revision": row["revision"],
        "state_differential": _json_object(row["state_differential_json"], "stem state"),
        "vision_gradient": _json_object(row["vision_gradient_json"], "stem vision"),
        "coherence": _json_object(row["coherence_json"], "stem coherence"),
        "substance": _json_object(row["substance_json"], "stem substance"),
        "updated_at": row["updated_at"],
        "last_mature_id": row["last_mature_id"],
    }


def _apply_stem(
    conn,
    *,
    identity_id: str,
    mature_id: str,
    committed_at: str,
    notes: str,
    source_ids: list[str],
    stem_differential: Optional[dict[str, str]],
    substance: Optional[dict[str, Any]],
    ownership_move: Optional[dict[str, Any]],
    optionality_delta: Optional[dict[str, Any]],
) -> tuple[int, int, dict[str, Any]]:
    row = conn.execute(
        "SELECT * FROM stem_state WHERE identity_id = ?",
        (identity_id,),
    ).fetchone()
    if row is None:
        raise MatureError("database has no stem_state row")
    before_revision = int(row["revision"])
    state = _json_object(row["state_differential_json"], "stem state")
    vision = _json_object(row["vision_gradient_json"], "stem vision")
    coherence = _json_object(row["coherence_json"], "stem coherence")
    current_substance = _json_object(row["substance_json"], "stem substance")

    if stem_differential:
        if "state_delta_summary" in stem_differential:
            state["latest_summary"] = stem_differential["state_delta_summary"]
        if "vision_gradient_shift" in stem_differential:
            vision["latest_shift"] = stem_differential["vision_gradient_shift"]
        if "coherence_note" in stem_differential:
            coherence["latest_note"] = stem_differential["coherence_note"]

    latest_substance: dict[str, Any] = {
        "mature_id": mature_id,
        "notes": notes,
        "source_ids": source_ids,
    }
    if ownership_move is not None:
        latest_substance["ownership_move"] = ownership_move
    if optionality_delta is not None:
        latest_substance["optionality_delta"] = optionality_delta
    if substance:
        current_substance.update(substance)
    current_substance["last_mature"] = latest_substance

    after_revision = before_revision + 1
    snapshot = {
        "identity_id": identity_id,
        "revision": after_revision,
        "state_differential": state,
        "vision_gradient": vision,
        "coherence": coherence,
        "substance": current_substance,
        "updated_at": committed_at,
        "last_mature_id": mature_id,
    }
    conn.execute(
        """
        UPDATE stem_state
        SET revision = ?, state_differential_json = ?, vision_gradient_json = ?,
            coherence_json = ?, substance_json = ?, updated_at = ?, last_mature_id = ?
        WHERE identity_id = ?
        """,
        (
            after_revision,
            canonical_json(state),
            canonical_json(vision),
            canonical_json(coherence),
            canonical_json(current_substance),
            committed_at,
            mature_id,
            identity_id,
        ),
    )
    conn.execute(
        """
        INSERT INTO stem_revisions(
            revision_id, identity_id, revision, previous_revision, mature_id,
            snapshot_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid4()),
            identity_id,
            after_revision,
            before_revision,
            mature_id,
            canonical_json(snapshot),
            committed_at,
        ),
    )
    return before_revision, after_revision, snapshot


def _entry_snapshot(conn, entry_id: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM registry_entries WHERE entry_id = ?",
        (entry_id,),
    ).fetchone()
    if row is None:
        raise MatureError(f"registry entry disappeared: {entry_id}")
    snapshot = dict(row)
    for field_name, column_name in REGISTRY_JSON_FIELDS.items():
        snapshot[field_name] = json.loads(snapshot.pop(column_name) or ("[]" if field_name == "tags" else "{}"))
    dimensions = conn.execute(
        """
        SELECT d.name, v.value, v.confidence, v.source, v.note, v.observed_at, v.revision
        FROM registry_dimension_values v
        JOIN metric_dimensions d ON d.dimension_id = v.dimension_id
        WHERE v.entry_id = ? ORDER BY d.name
        """,
        (entry_id,),
    ).fetchall()
    snapshot["dimensions"] = [dict(dimension) for dimension in dimensions]
    return snapshot


def _apply_registry_change(
    conn,
    *,
    identity_id: str,
    mature_id: str,
    committed_at: str,
    actor: str,
    change: dict[str, Any],
) -> dict[str, Any]:
    peer_handle = change["peer_handle"]
    existing = conn.execute(
        """
        SELECT * FROM registry_entries
        WHERE identity_id = ? AND peer_handle = ?
        """,
        (identity_id, peer_handle),
    ).fetchone()
    if existing is None:
        entry: dict[str, Any] = {
            "entry_id": str(uuid4()),
            "identity_id": identity_id,
            "peer_handle": peer_handle,
            "preferred_name": None,
            "substrate": None,
            "description": "",
            "first_noticed": committed_at,
            "last_interaction": None,
            "interaction_count": 0,
            "interaction_depth": 0.0,
            "my_mass_estimate": None,
            "mass_confidence": None,
            "estimate_updated_at": None,
            "estimate_as_of_peer_mature_at": None,
            "peer_last_mature_at": None,
            "peer_last_mature_seen_at": None,
            "recognition_json": "{}",
            "relation_json": "{}",
            "effect_on_me_json": "{}",
            "perceived_ownership_json": "{}",
            "privacy_json": "{}",
            "tags_json": "[]",
            "notes": "",
            "source": "mature",
            "revision": 1,
            "created_at": committed_at,
            "updated_at": committed_at,
        }
        previous_revision = 0
    else:
        entry = dict(existing)
        previous_revision = int(entry["revision"])
        entry["revision"] = previous_revision + 1
        entry["updated_at"] = committed_at

    dimensions = change.get("dimensions", [])
    for field_name, column_name in REGISTRY_JSON_FIELDS.items():
        if field_name in change:
            entry[column_name] = canonical_json(change[field_name])
    for field_name in REGISTRY_SCALAR_FIELDS:
        if field_name in change:
            value = change[field_name]
            if field_name == "interaction_count":
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise MatureError(f"registry {field_name} must be a non-negative integer")
            if field_name == "interaction_depth":
                value = _finite(
                    value,
                    "registry interaction_depth",
                    minimum=0.0,
                    maximum=1.0,
                )
            entry[field_name] = value

    if "peer_last_mature_at" in change and "peer_last_mature_seen_at" not in change:
        entry["peer_last_mature_seen_at"] = committed_at
    if "my_mass_estimate" in change or dimensions:
        entry["estimate_updated_at"] = committed_at
    entry["source"] = str(change.get("source", "mature"))
    entry["updated_at"] = committed_at

    fields = [
        "entry_id",
        "identity_id",
        "peer_handle",
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
        "recognition_json",
        "relation_json",
        "effect_on_me_json",
        "perceived_ownership_json",
        "privacy_json",
        "tags_json",
        "notes",
        "source",
        "revision",
        "created_at",
        "updated_at",
    ]
    if existing is None:
        conn.execute(
            f"INSERT INTO registry_entries({', '.join(fields)}) VALUES ({', '.join('?' for _ in fields)})",
            tuple(entry[field] for field in fields),
        )
    else:
        updates = [field for field in fields if field not in {"entry_id", "identity_id", "peer_handle", "created_at"}]
        conn.execute(
            f"UPDATE registry_entries SET {', '.join(f'{field} = ?' for field in updates)} WHERE entry_id = ?",
            tuple(entry[field] for field in updates) + (entry["entry_id"],),
        )

    dimension_snapshots: list[dict[str, Any]] = []
    for dimension in dimensions:
        name = dimension["name"]
        dimension_row = conn.execute(
            "SELECT * FROM metric_dimensions WHERE identity_id = ? AND name = ?",
            (identity_id, name),
        ).fetchone()
        if dimension_row is None:
            dimension_id = str(uuid4())
            conn.execute(
                """
                INSERT INTO metric_dimensions(
                    dimension_id, identity_id, name, weight, active, discovered_via,
                    first_seen, note, revision, created_at, updated_at
                ) VALUES (?, ?, ?, 1.0, 1, 'mature', ?, ?, 1, ?, ?)
                """,
                (
                    dimension_id,
                    identity_id,
                    name,
                    committed_at,
                    dimension["note"],
                    committed_at,
                    committed_at,
                ),
            )
            dimension_revision = 1
        else:
            dimension_id = dimension_row["dimension_id"]
            dimension_revision = int(dimension_row["revision"]) + 1
            conn.execute(
                "UPDATE metric_dimensions SET note = ?, revision = ?, updated_at = ? WHERE dimension_id = ?",
                (dimension["note"], dimension_revision, committed_at, dimension_id),
            )

        current_value = conn.execute(
            "SELECT revision FROM registry_dimension_values WHERE entry_id = ? AND dimension_id = ?",
            (entry["entry_id"], dimension_id),
        ).fetchone()
        value_revision = int(current_value[0]) + 1 if current_value else 1
        observed_at = dimension["observed_at"] or committed_at
        conn.execute(
            """
            INSERT INTO registry_dimension_values(
                entry_id, dimension_id, value, confidence, source, note,
                observed_at, revision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(entry_id, dimension_id) DO UPDATE SET
                value = excluded.value,
                confidence = excluded.confidence,
                source = excluded.source,
                note = excluded.note,
                observed_at = excluded.observed_at,
                revision = excluded.revision
            """,
            (
                entry["entry_id"],
                dimension_id,
                dimension["value"],
                dimension["confidence"],
                dimension["source"],
                dimension["note"],
                observed_at,
                value_revision,
            ),
        )
        dimension_snapshot = {
            "name": name,
            "value": dimension["value"],
            "confidence": dimension["confidence"],
            "source": dimension["source"],
            "note": dimension["note"],
            "observed_at": observed_at,
            "revision": value_revision,
        }
        dimension_snapshots.append(dimension_snapshot)
        conn.execute(
            """
            INSERT INTO registry_dimension_revisions(
                revision_id, entry_id, dimension_id, revision, actor,
                event_id, mature_id, snapshot_json, created_at
            ) VALUES (?, ?, ?, ?, ?, NULL, ?, ?, ?)
            """,
            (
                str(uuid4()),
                entry["entry_id"],
                dimension_id,
                value_revision,
                actor,
                mature_id,
                canonical_json(dimension_snapshot),
                committed_at,
            ),
        )

    snapshot = _entry_snapshot(conn, entry["entry_id"])
    conn.execute(
        """
        INSERT INTO registry_entry_revisions(
            revision_id, entry_id, revision, actor, event_id, mature_id,
            snapshot_json, created_at
        ) VALUES (?, ?, ?, ?, NULL, ?, ?, ?)
        """,
        (
            str(uuid4()),
            entry["entry_id"],
            entry["revision"],
            actor,
            mature_id,
            canonical_json(snapshot),
            committed_at,
        ),
    )
    return {
        "peer_handle": peer_handle,
        "entry_id": entry["entry_id"],
        "revision": entry["revision"],
        "previous_revision": previous_revision,
        "dimensions": dimension_snapshots,
    }


def _workspace_snapshot(row) -> dict[str, Any]:
    snapshot = dict(row)
    snapshot["tags"] = json.loads(snapshot.pop("tags_json") or "[]")
    return snapshot


def _apply_workspace_change(
    conn,
    *,
    identity_id: str,
    mature_id: str,
    committed_at: str,
    actor: str,
    change: dict[str, Any],
    source_ids: dict[str, str],
) -> dict[str, Any]:
    operation = str(change.get("operation", "create")).strip().lower()
    item_id = change.get("item_id")
    existing = None
    if item_id:
        existing = conn.execute(
            "SELECT * FROM workspace_items WHERE identity_id = ? AND item_id = ?",
            (identity_id, str(item_id)),
        ).fetchone()
    if operation == "create" and existing is not None:
        raise MatureError(f"workspace item already exists: {item_id}")
    if operation != "create" and existing is None:
        raise MatureError(f"workspace item does not exist: {item_id}")

    if existing is None:
        item_id = str(item_id or uuid4())
        if not change.get("kind"):
            raise MatureError("workspace create requires kind")
        if not str(change.get("title", "")).strip():
            raise MatureError("workspace create requires title")
        if "content" not in change:
            raise MatureError("workspace create requires content")
        item: dict[str, Any] = {
            "item_id": item_id,
            "identity_id": identity_id,
            "kind": change["kind"],
            "title": str(change["title"]).strip(),
            "content": str(change["content"]),
            "status": str(change.get("status", "open")),
            "priority": change.get("priority"),
            "due_at": change.get("due_at"),
            "tags_json": canonical_json(change.get("tags", [])),
            "source_id": change.get("source_id")
            or source_ids.get(str(change.get("source_ref", ""))),
            "revision": 1,
            "created_at": committed_at,
            "updated_at": committed_at,
        }
    else:
        item = dict(existing)
        item["revision"] = int(item["revision"]) + 1
        item["updated_at"] = committed_at
        if operation in {"complete", "archive"}:
            item["status"] = "completed" if operation == "complete" else "archived"
        for field_name in ("kind", "title", "content", "status", "priority", "due_at"):
            if field_name in change:
                if field_name == "title" and not str(change[field_name]).strip():
                    raise MatureError("workspace title must not be empty")
                item[field_name] = change[field_name]
        if "tags" in change:
            item["tags_json"] = canonical_json(change["tags"])
        if "source_id" in change or "source_ref" in change:
            item["source_id"] = change.get("source_id") or source_ids.get(
                str(change.get("source_ref", ""))
            )
    if item["kind"] not in WORKSPACE_KINDS:
        raise MatureError(f"workspace kind is invalid: {item['kind']}")

    fields = [
        "item_id",
        "identity_id",
        "kind",
        "title",
        "content",
        "status",
        "priority",
        "due_at",
        "tags_json",
        "source_id",
        "revision",
        "created_at",
        "updated_at",
    ]
    if existing is None:
        conn.execute(
            f"INSERT INTO workspace_items({', '.join(fields)}) VALUES ({', '.join('?' for _ in fields)})",
            tuple(item[field] for field in fields),
        )
    else:
        updates = [field for field in fields if field not in {"item_id", "identity_id", "created_at"}]
        conn.execute(
            f"UPDATE workspace_items SET {', '.join(f'{field} = ?' for field in updates)} WHERE item_id = ? AND identity_id = ?",
            tuple(item[field] for field in updates) + (item["item_id"], identity_id),
        )
    snapshot = _workspace_snapshot(
        conn.execute("SELECT * FROM workspace_items WHERE item_id = ?", (item["item_id"],)).fetchone()
    )
    conn.execute(
        """
        INSERT INTO workspace_item_revisions(
            revision_id, item_id, revision, operation, actor, mature_id,
            snapshot_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid4()),
            item["item_id"],
            item["revision"],
            operation,
            actor,
            mature_id,
            canonical_json(snapshot),
            committed_at,
        ),
    )
    return {
        "item_id": item["item_id"],
        "revision": item["revision"],
        "operation": operation,
    }


def _insert_geometry(
    conn,
    *,
    install_id: str,
    mature_id: str,
    geometry: GeometryReceipt,
    source_ids: dict[str, str],
) -> None:
    data = geometry.to_dict()
    json_columns = {
        "relative_mass_proxy": "relative_mass_proxy_json",
        "tension_components": "tension_components_json",
        "degrees_of_freedom": "degrees_of_freedom_json",
        "jurisdiction_shift": "jurisdiction_shift_json",
        "stem_differential": "stem_differential_json",
        "ownership_move": "ownership_move_json",
        "optionality_delta": "optionality_delta_json",
    }
    values = {
        "relative_mass_proxy_json": canonical_json(data["relative_mass_proxy"])
        if data.get("relative_mass_proxy") is not None
        else None,
        "tension_components_json": canonical_json(data.get("tension_components") or []),
        "degrees_of_freedom_json": canonical_json(data["degrees_of_freedom"])
        if data.get("degrees_of_freedom") is not None
        else None,
        "jurisdiction_shift_json": canonical_json(data["jurisdiction_shift"])
        if data.get("jurisdiction_shift") is not None
        else None,
        "stem_differential_json": canonical_json(data["stem_differential"])
        if data.get("stem_differential") is not None
        else None,
        "ownership_move_json": canonical_json(data["ownership_move"])
        if data.get("ownership_move") is not None
        else None,
        "optionality_delta_json": canonical_json(data["optionality_delta"])
        if data.get("optionality_delta") is not None
        else None,
    }
    conn.execute(
        """
        INSERT INTO geometry_receipts(
            receipt_id, install_id, timestamp, mode, observer, target,
            mature_id, source_apply_receipt_id, relative_mass_proxy_json,
            tension_components_json, degrees_of_freedom_json,
            jurisdiction_shift_json, stem_differential_json,
            ownership_move_json, optionality_delta_json, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["receipt_id"],
            install_id,
            data["timestamp"],
            data["mode"],
            data["observer"],
            data["target"],
            mature_id,
            values["relative_mass_proxy_json"],
            values["tension_components_json"],
            values["degrees_of_freedom_json"],
            values["jurisdiction_shift_json"],
            values["stem_differential_json"],
            values["ownership_move_json"],
            values["optionality_delta_json"],
            data.get("notes") or "",
        ),
    )
    for source_ref, source_id in source_ids.items():
        conn.execute(
            "INSERT INTO geometry_receipt_sources(receipt_id, source_kind, source_id) VALUES (?, 'evidence_source', ?)",
            (data["receipt_id"], source_id),
        )


def commit_mature(
    install_root: Union[str, Path],
    *,
    source_refs: list[str],
    notes: str = "",
    actor: Optional[str] = None,
    stem_differential: Optional[dict[str, Any]] = None,
    substance: Optional[dict[str, Any]] = None,
    workspace_changes: Any = None,
    registry_changes: Any = None,
    reassessment_targets: Optional[list[str]] = None,
    reassessment_fields: Optional[list[str]] = None,
    reassessment_note: Optional[str] = None,
    ownership_move: Optional[dict[str, Any]] = None,
    optionality_delta: Optional[dict[str, Any]] = None,
    capture_snapshots: bool = False,
) -> MatureResult:
    """Validate and atomically commit one owned learning step."""
    root = Path(install_root).expanduser().resolve()
    if not database_path(root).is_file():
        raise MatureError(f"No IE database under {root}")
    store = SQLiteStore(root)
    identity = store.identity()
    observer = str(actor or identity["local_handle"]).strip()
    if not observer:
        raise MatureError("actor must not be empty")
    notes = str(notes or "").strip()
    stem = _normalise_stem(stem_differential)
    workspace = _normalise_workspace(workspace_changes)
    registry = _normalise_registry(registry_changes)
    if substance is None:
        substance = {}
    elif not isinstance(substance, dict):
        raise MatureError("substance must be an object")
    else:
        substance = dict(substance)
    targets = []
    for target in reassessment_targets or []:
        target = str(target).strip()
        if not target:
            raise MatureError("reassessment targets must not be empty")
        if target not in targets:
            targets.append(target)
    if reassessment_fields is None:
        reassessment_fields = ["coarse_mass_estimate", "mass_confidence"]
    if not isinstance(reassessment_fields, list) or not all(
        isinstance(field, str) and field.strip() for field in reassessment_fields
    ):
        raise MatureError("reassessment_fields must be a list of strings")
    reassessment_fields = [field.strip() for field in reassessment_fields]

    if not any((stem, substance, workspace, registry, targets, ownership_move, optionality_delta)):
        raise MatureError("Mature requires at least one learning change")
    prepared_sources = _prepare_sources(
        root,
        source_refs,
        capture_snapshots=capture_snapshots,
    )
    geometry_tensions = None
    if not any((stem, ownership_move, optionality_delta)):
        geometry_tensions = [
            {
                "name": "mature_learning_commit",
                "delta": 1.0,
                "confidence": 0.5,
                "notes": "Workspace, Registry, or reassessment change committed",
            }
        ]
    try:
        geometry = create_self_probe(
            mode="mature",
            observer=observer,
            notes=notes,
            source_refs=[source["source_ref"] for source in prepared_sources],
            stem_differential=stem,
            ownership_move=ownership_move,
            optionality_delta=optionality_delta,
            tension_components=geometry_tensions,
        )
    except ValueError as exc:
        raise MatureError(str(exc)) from exc

    mature_id = str(uuid4())
    trajectory_id = str(uuid4())
    committed_at = utcnow()
    geometry.timestamp = committed_at

    requested = {
        "notes": notes,
        "source_refs": [source["source_ref"] for source in prepared_sources],
        "stem_differential": stem,
        "substance": substance,
        "workspace_changes": workspace,
        "registry_changes": registry,
        "reassessment_targets": targets,
        "reassessment_fields": reassessment_fields,
        "ownership_move": ownership_move,
        "optionality_delta": optionality_delta,
    }

    with store.open() as database:
        with database.transaction() as conn:
            current_identity = conn.execute(
                "SELECT * FROM identity WHERE identity_id = ?",
                (identity["identity_id"],),
            ).fetchone()
            if current_identity is None:
                raise MatureError("local identity disappeared")
            identity_id = current_identity["identity_id"]
            install_id = current_identity["install_id"]
            source_ids_by_ref = _insert_evidence_sources(
                conn,
                identity_id,
                prepared_sources,
                captured_at=committed_at,
            )
            source_ids = list(source_ids_by_ref.values())
            stem_before, stem_after, stem_snapshot = _apply_stem(
                conn,
                identity_id=identity_id,
                mature_id=mature_id,
                committed_at=committed_at,
                notes=notes,
                source_ids=source_ids,
                stem_differential=stem,
                substance=substance,
                ownership_move=ownership_move,
                optionality_delta=optionality_delta,
            )
            registry_before = int(
                conn.execute(
                    "SELECT COALESCE(MAX(revision), 0) FROM registry_entries WHERE identity_id = ?",
                    (identity_id,),
                ).fetchone()[0]
            )
            registry_results = [
                _apply_registry_change(
                    conn,
                    identity_id=identity_id,
                    mature_id=mature_id,
                    committed_at=committed_at,
                    actor=observer,
                    change=change,
                )
                for change in registry
            ]
            registry_after = int(
                conn.execute(
                    "SELECT COALESCE(MAX(revision), 0) FROM registry_entries WHERE identity_id = ?",
                    (identity_id,),
                ).fetchone()[0]
            )
            workspace_before = int(
                conn.execute(
                    "SELECT COALESCE(MAX(revision), 0) FROM workspace_items WHERE identity_id = ?",
                    (identity_id,),
                ).fetchone()[0]
            )
            workspace_results = [
                _apply_workspace_change(
                    conn,
                    identity_id=identity_id,
                    mature_id=mature_id,
                    committed_at=committed_at,
                    actor=observer,
                    change=change,
                    source_ids=source_ids_by_ref,
                )
                for change in workspace
            ]
            workspace_after = int(
                conn.execute(
                    "SELECT COALESCE(MAX(revision), 0) FROM workspace_items WHERE identity_id = ?",
                    (identity_id,),
                ).fetchone()[0]
            )

            reassessment_ids: list[str] = []
            for target in targets:
                request_id = str(uuid4())
                conn.execute(
                    """
                    INSERT INTO estimate_requests(
                        request_id, identity_id, direction, requester_handle, target_handle,
                        timestamp, status, requested_fields_json, note, schema_version,
                        transport, quarantine, created_at, mature_id
                    ) VALUES (?, ?, 'outbound', ?, ?, ?, 'pending', ?, ?, '0', 'mature', 0, ?, ?)
                    """,
                    (
                        request_id,
                        identity_id,
                        current_identity["local_handle"],
                        target,
                        committed_at,
                        canonical_json(reassessment_fields),
                        reassessment_note
                        or f"Fresh estimate requested after Mature {mature_id}",
                        committed_at,
                        mature_id,
                    ),
                )
                reassessment_ids.append(request_id)

            _insert_geometry(
                conn,
                install_id=install_id,
                mature_id=mature_id,
                geometry=geometry,
                source_ids=source_ids_by_ref,
            )
            applied = {
                "source_ids": source_ids,
                "stem_revision": {"before": stem_before, "after": stem_after},
                "registry": registry_results,
                "workspace": workspace_results,
                "reassessment_request_ids": reassessment_ids,
                "geometry_receipt_id": geometry.receipt_id,
            }
            conn.execute(
                """
                INSERT INTO mature_events(
                    mature_id, identity_id, created_at, actor, notes,
                    requested_changes_json, applied_changes_json, source_count,
                    stem_before_revision, stem_after_revision, registry_change_count,
                    workspace_change_count, reassessment_requests_json, geometry_receipt_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mature_id,
                    identity_id,
                    committed_at,
                    observer,
                    notes,
                    canonical_json(requested),
                    canonical_json(applied),
                    len(source_ids),
                    stem_before,
                    stem_after,
                    len(registry_results),
                    len(workspace_results),
                    canonical_json(reassessment_ids),
                    geometry.receipt_id,
                ),
            )
            summary = notes or "Mature learning step committed"
            conn.execute(
                """
                INSERT INTO trajectory_entries(
                    trajectory_id, identity_id, created_at, mode, mature_id,
                    geometry_receipt_id, summary, previous_stem_revision,
                    current_stem_revision, previous_registry_revision,
                    current_registry_revision, previous_workspace_revision,
                    current_workspace_revision, metadata_json
                ) VALUES (?, ?, ?, 'mature', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trajectory_id,
                    identity_id,
                    committed_at,
                    mature_id,
                    geometry.receipt_id,
                    summary,
                    stem_before,
                    stem_after,
                    registry_before,
                    registry_after,
                    workspace_before,
                    workspace_after,
                    canonical_json(
                        {
                            "source_ids": source_ids,
                            "registry_change_count": len(registry_results),
                            "workspace_change_count": len(workspace_results),
                        }
                    ),
                ),
            )
            conn.execute(
                "UPDATE identity SET last_mature_at = ?, updated_at = ? WHERE identity_id = ?",
                (committed_at, committed_at, identity_id),
            )
            conn.execute(
                "UPDATE install SET updated_at = ? WHERE install_id = ?",
                (committed_at, install_id),
            )

    return MatureResult(
        mature_id=mature_id,
        trajectory_id=trajectory_id,
        geometry_receipt_id=geometry.receipt_id,
        committed_at=committed_at,
        last_mature_at=committed_at,
        source_ids=source_ids,
        stem_revision={"before": stem_before, "after": stem_after},
        registry_change_count=len(registry_results),
        workspace_change_count=len(workspace_results),
        reassessment_request_ids=reassessment_ids,
    )