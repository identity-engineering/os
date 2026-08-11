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
GRANT_SCOPES = (
    "policy_admin",
    "visibility_control",
    "surface_admin",
    "grant_admin",
    "residual_emergency",
)


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


def list_grants(
    install_root: Union[str, Path],
    *,
    object_identity_id: Optional[str] = None,
    actor_identity_id: Optional[str] = None,
    include_revoked: bool = False,
) -> list[dict[str, Any]]:
    """List grants visible from the local Identity's jurisdiction surface."""
    root = Path(install_root).expanduser().resolve()
    db_path = database_path(root)
    if not db_path.is_file():
        raise JurisdictionError(f"No IE database under {root}")

    with Database(db_path) as database:
        local_identity = _local_identity(database.conn)
        object_id = object_identity_id or str(local_identity["identity_id"])
        conditions = ["object_identity_id = ?"]
        parameters: list[Any] = [object_id]
        if actor_identity_id:
            conditions.append("actor_identity_id = ?")
            parameters.append(actor_identity_id)
        if not include_revoked:
            conditions.append("revoked_at IS NULL")
        rows = database.conn.execute(
            "SELECT * FROM identity_grants WHERE "
            + " AND ".join(conditions)
            + " ORDER BY granted_at, grant_id",
            parameters,
        ).fetchall()
    return [_grant_row_to_dict(row) for row in rows]


def transfer_grant(
    install_root: Union[str, Path],
    *,
    grant_id: str,
    to_identity_id: str,
    note: str = "",
) -> dict[str, Any]:
    """Transfer one active ordinary grant and revoke the source atomically."""
    root = Path(install_root).expanduser().resolve()
    db_path = database_path(root)
    if not db_path.is_file():
        raise JurisdictionError(f"No IE database under {root}")
    if not grant_id.strip() or not to_identity_id.strip():
        raise JurisdictionError("grant_id and to_identity_id are required")

    now = utcnow()
    with Database(db_path) as database:
        with database.transaction() as conn:
            local_identity = _local_identity(conn)
            actor_id = str(local_identity["identity_id"])
            grant = conn.execute(
                "SELECT * FROM identity_grants WHERE grant_id = ?",
                (grant_id,),
            ).fetchone()
            if grant is None:
                raise JurisdictionError(f"grant not found: {grant_id}")
            if grant["revoked_at"] is not None:
                raise JurisdictionError("cannot transfer a revoked grant")
            if str(grant["actor_identity_id"]) != actor_id:
                raise JurisdictionError("local Identity does not hold this grant")
            if bool(grant["residual"]):
                raise JurisdictionError("residual emergency grants are not transferable")
            if not bool(grant["transferable"]):
                raise JurisdictionError("grant is marked non-transferable")
            if str(grant["actor_identity_id"]) == to_identity_id:
                raise JurisdictionError("grant target must differ from current holder")
            target = conn.execute(
                "SELECT identity_id FROM identity WHERE identity_id = ?",
                (to_identity_id,),
            ).fetchone()
            if target is None:
                raise JurisdictionError(f"target Identity not found: {to_identity_id}")
            duplicate = conn.execute(
                """
                SELECT 1 FROM identity_grants
                WHERE actor_identity_id = ?
                  AND object_identity_id = ?
                  AND scope = ?
                  AND revoked_at IS NULL
                  AND space_id IS ?
                LIMIT 1
                """,
                (
                    to_identity_id,
                    grant["object_identity_id"],
                    grant["scope"],
                    grant["space_id"],
                ),
            ).fetchone()
            if duplicate is not None:
                raise JurisdictionError("target Identity already holds this scope")

            conn.execute(
                """
                UPDATE identity_grants
                SET revoked_at = ?, revoked_by_identity_id = ?, revocation_note = ?
                WHERE grant_id = ? AND revoked_at IS NULL
                """,
                (now, actor_id, note or "transferred", grant_id),
            )
            new_grant_id = str(uuid4())
            conn.execute(
                """
                INSERT INTO identity_grants(
                    grant_id, actor_identity_id, object_identity_id, scope, residual,
                    transferable, space_id, granted_at, revoked_at,
                    granted_by_identity_id, note, revoked_by_identity_id, revocation_note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, NULL, '')
                """,
                (
                    new_grant_id,
                    to_identity_id,
                    grant["object_identity_id"],
                    grant["scope"],
                    grant["residual"],
                    grant["transferable"],
                    grant["space_id"],
                    now,
                    actor_id,
                    note or "transferred",
                ),
            )

    return {
        "status": "transferred",
        "actor_identity_id": actor_id,
        "source_grant_id": grant_id,
        "grant_id": new_grant_id,
        "target_identity_id": to_identity_id,
        "object_identity_id": str(grant["object_identity_id"]),
        "scope": str(grant["scope"]),
        "space_id": grant["space_id"],
        "transferred_at": now,
        "note": note or "transferred",
    }


def revoke_grant(
    install_root: Union[str, Path],
    *,
    grant_id: str,
    note: str = "",
) -> dict[str, Any]:
    """Revoke an ordinary grant by the object Identity or its grant admin."""
    root = Path(install_root).expanduser().resolve()
    db_path = database_path(root)
    if not db_path.is_file():
        raise JurisdictionError(f"No IE database under {root}")
    if not grant_id.strip():
        raise JurisdictionError("grant_id is required")

    now = utcnow()
    with Database(db_path) as database:
        with database.transaction() as conn:
            local_identity = _local_identity(conn)
            actor_id = str(local_identity["identity_id"])
            grant = conn.execute(
                "SELECT * FROM identity_grants WHERE grant_id = ?",
                (grant_id,),
            ).fetchone()
            if grant is None:
                raise JurisdictionError(f"grant not found: {grant_id}")
            if grant["revoked_at"] is not None:
                raise JurisdictionError("grant is already revoked")
            if bool(grant["residual"]):
                raise JurisdictionError("residual emergency grants require a separate emergency path")
            object_id = str(grant["object_identity_id"])
            is_object = actor_id == object_id
            has_admin = conn.execute(
                """
                SELECT 1 FROM identity_grants
                WHERE actor_identity_id = ?
                  AND object_identity_id = ?
                  AND scope = 'grant_admin'
                  AND residual = 0
                  AND revoked_at IS NULL
                  AND (space_id IS NULL OR space_id IS ?)
                LIMIT 1
                """,
                (actor_id, object_id, grant["space_id"]),
            ).fetchone()
            if not is_object and has_admin is None:
                raise JurisdictionError("local Identity cannot revoke this grant")
            reason = note or "revoked"
            conn.execute(
                """
                UPDATE identity_grants
                SET revoked_at = ?, revoked_by_identity_id = ?, revocation_note = ?
                WHERE grant_id = ? AND revoked_at IS NULL
                """,
                (now, actor_id, reason, grant_id),
            )

    return {
        "status": "revoked",
        "actor_identity_id": actor_id,
        "grant_id": grant_id,
        "object_identity_id": object_id,
        "target_identity_id": str(grant["actor_identity_id"]),
        "scope": str(grant["scope"]),
        "space_id": grant["space_id"],
        "revoked_at": now,
        "note": reason,
    }


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


def _grant_row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "grant_id": row["grant_id"],
        "actor_identity_id": row["actor_identity_id"],
        "object_identity_id": row["object_identity_id"],
        "scope": row["scope"],
        "residual": bool(row["residual"]),
        "transferable": bool(row["transferable"]),
        "space_id": row["space_id"],
        "granted_at": row["granted_at"],
        "revoked_at": row["revoked_at"],
        "granted_by_identity_id": row["granted_by_identity_id"],
        "note": row["note"] or "",
        "revoked_by_identity_id": row["revoked_by_identity_id"],
        "revocation_note": row["revocation_note"] or "",
    }
