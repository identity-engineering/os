"""Access & Jurisdiction probes — owner-gated measurement of degrees of freedom."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional, Union
from uuid import uuid4

from .database import Database, DatabaseError, canonical_json, database_path, utcnow


class JurisdictionError(RuntimeError):
    """Raised when an Access/Jurisdiction probe cannot be written or read."""


ACCESS_FIELDS = ("reach", "use", "observe", "affected_by")
JURISDICTION_FIELDS = (
    "decide_goals",
    "constrain",
    "transfer",
    "destroy",
    "redefine_boundary",
)
OBJECT_KINDS = ("self", "peer", "stem_aspect", "space")


def _parse_object_ref(object_spec: str) -> tuple[str, str]:
    """Parse 'peer:alice' | 'self' | 'stem:vision' | 'space:<id>' into kind + ref."""
    raw = (object_spec or "").strip()
    if not raw:
        raise JurisdictionError("object is required (e.g. self, peer:alice)")
    if raw == "self" or raw.startswith("self:"):
        return "self", "self"
    if ":" in raw:
        kind, _, ref = raw.partition(":")
        kind = kind.strip().lower()
        ref = ref.strip()
        if kind not in OBJECT_KINDS:
            raise JurisdictionError(
                f"object kind must be one of {OBJECT_KINDS}; got {kind!r}"
            )
        if not ref:
            raise JurisdictionError(f"object ref missing after {kind}:")
        return kind, ref
    # bare handle → peer
    return "peer", raw


def _normalize_layer(layer: dict[str, Any], allowed: tuple[str, ...], label: str) -> dict[str, Any]:
    if not isinstance(layer, dict):
        raise JurisdictionError(f"{label} must be a JSON object")
    out: dict[str, Any] = {}
    for key, value in layer.items():
        if key not in allowed and key not in {"notes", "residual", "tags"}:
            # allow extra qualitative keys but keep known fields first-class
            out[key] = value
            continue
        if isinstance(value, (int, float)):
            score = float(value)
            if not (0.0 <= score <= 1.0):
                raise JurisdictionError(f"{label}.{key} score must be in [0, 1]")
            out[key] = score
        elif isinstance(value, str):
            out[key] = value.strip()
        elif isinstance(value, dict):
            out[key] = value
        else:
            out[key] = value
    return out


def _local_identity(conn) -> Any:
    row = conn.execute("SELECT * FROM identity LIMIT 1").fetchone()
    if row is None:
        raise JurisdictionError("no local identity in database")
    return row


def write_profile(
    install_root: Union[str, Path],
    *,
    object_spec: str,
    access: dict[str, Any],
    jurisdiction: dict[str, Any],
    confidence: float = 0.5,
    notes: str = "",
    source: str = "owner_probe",
) -> dict[str, Any]:
    """Owner-gated write of an Access + Jurisdiction profile (V1: local Identity only)."""
    if not (0.0 <= float(confidence) <= 1.0):
        raise JurisdictionError("confidence must be in [0, 1]")

    object_kind, object_ref = _parse_object_ref(object_spec)
    access_norm = _normalize_layer(access, ACCESS_FIELDS, "access")
    juris_norm = _normalize_layer(jurisdiction, JURISDICTION_FIELDS, "jurisdiction")

    root = Path(install_root).expanduser().resolve()
    db_path = database_path(root)
    if not db_path.is_file():
        raise JurisdictionError(f"No IE database under {root}")

    now = utcnow()
    with Database(db_path) as database:
        with database.transaction() as conn:
            identity = _local_identity(conn)
            identity_id = identity["identity_id"]

            existing = conn.execute(
                """
                SELECT profile_id, revision FROM access_jurisdiction_profiles
                WHERE observer_identity_id = ?
                  AND object_kind = ?
                  AND object_ref = ?
                ORDER BY revision DESC LIMIT 1
                """,
                (identity_id, object_kind, object_ref),
            ).fetchone()

            revision = int(existing["revision"]) + 1 if existing else 1
            profile_id = str(uuid4())

            conn.execute(
                """
                INSERT INTO access_jurisdiction_profiles(
                    profile_id, observer_identity_id, object_kind, object_ref,
                    observed_at, confidence, access_json, jurisdiction_json,
                    notes, source, revision, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    identity_id,
                    object_kind,
                    object_ref,
                    now,
                    float(confidence),
                    canonical_json(access_norm),
                    canonical_json(juris_norm),
                    notes or "",
                    source,
                    revision,
                    now,
                    now,
                ),
            )

            # Lightweight mirror into Registry perceived_ownership for peers
            if object_kind == "peer":
                entry = conn.execute(
                    """
                    SELECT entry_id, revision FROM registry_entries
                    WHERE identity_id = ? AND peer_handle = ?
                    """,
                    (identity_id, object_ref),
                ).fetchone()
                if entry is not None:
                    summary = {
                        "profile_id": profile_id,
                        "observed_at": now,
                        "confidence": float(confidence),
                        "access": access_norm,
                        "jurisdiction": juris_norm,
                        "source": source,
                    }
                    new_rev = int(entry["revision"]) + 1
                    conn.execute(
                        """
                        UPDATE registry_entries
                        SET perceived_ownership_json = ?, revision = ?, updated_at = ?
                        WHERE entry_id = ?
                        """,
                        (canonical_json(summary), new_rev, now, entry["entry_id"]),
                    )

    return {
        "profile_id": profile_id,
        "observer_identity_id": identity_id,
        "object_kind": object_kind,
        "object_ref": object_ref,
        "observed_at": now,
        "confidence": float(confidence),
        "access": access_norm,
        "jurisdiction": juris_norm,
        "notes": notes or "",
        "source": source,
        "revision": revision,
    }


def get_profile(
    install_root: Union[str, Path],
    *,
    object_spec: str,
) -> Optional[dict[str, Any]]:
    """Return the latest profile for the given object, or None."""
    object_kind, object_ref = _parse_object_ref(object_spec)
    root = Path(install_root).expanduser().resolve()
    db_path = database_path(root)
    if not db_path.is_file():
        raise JurisdictionError(f"No IE database under {root}")

    with Database(db_path) as database:
        identity = _local_identity(database.conn)
        row = database.conn.execute(
            """
            SELECT * FROM access_jurisdiction_profiles
            WHERE observer_identity_id = ?
              AND object_kind = ?
              AND object_ref = ?
            ORDER BY revision DESC LIMIT 1
            """,
            (identity["identity_id"], object_kind, object_ref),
        ).fetchone()
    if row is None:
        return None
    return _row_to_dict(row)


def list_profiles(install_root: Union[str, Path]) -> list[dict[str, Any]]:
    """List latest profile per object for the local Identity."""
    root = Path(install_root).expanduser().resolve()
    db_path = database_path(root)
    if not db_path.is_file():
        raise JurisdictionError(f"No IE database under {root}")

    with Database(db_path) as database:
        identity = _local_identity(database.conn)
        rows = database.conn.execute(
            """
            SELECT p.*
            FROM access_jurisdiction_profiles p
            INNER JOIN (
                SELECT object_kind, object_ref, MAX(revision) AS max_rev
                FROM access_jurisdiction_profiles
                WHERE observer_identity_id = ?
                GROUP BY object_kind, object_ref
            ) latest
              ON p.object_kind = latest.object_kind
             AND p.object_ref = latest.object_ref
             AND p.revision = latest.max_rev
            WHERE p.observer_identity_id = ?
            ORDER BY p.object_kind, p.object_ref
            """,
            (identity["identity_id"], identity["identity_id"]),
        ).fetchall()
    return [_row_to_dict(row) for row in rows]


def _row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "profile_id": row["profile_id"],
        "observer_identity_id": row["observer_identity_id"],
        "object_kind": row["object_kind"],
        "object_ref": row["object_ref"],
        "observed_at": row["observed_at"],
        "confidence": row["confidence"],
        "access": json.loads(row["access_json"]) if row["access_json"] else {},
        "jurisdiction": json.loads(row["jurisdiction_json"])
        if row["jurisdiction_json"]
        else {},
        "notes": row["notes"] or "",
        "source": row["source"],
        "revision": row["revision"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
