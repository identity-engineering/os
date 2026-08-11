"""Public Space boundary descriptors and safe inbound validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional, Union

from .database import (
    DEFAULT_SPACE_MEMBRANE_POLICY,
    Database,
    DatabaseError,
    canonical_json,
    database_path,
    sha256_text,
    utcnow,
)

MEMBRANE_FORMAT = "identity-engineering.space-boundary"
MEMBRANE_FORMAT_VERSION = 1


class MembraneError(ValueError):
    """Raised when a Space boundary cannot be exported or accepted."""


SPACE_CAPABILITIES = ("surface", "interaction_signal", "public_card", "private_geometry")


def list_spaces(
    install_root: Union[str, Path],
    *,
    include_revoked: bool = False,
) -> list[dict[str, Any]]:
    """List locally known Space descriptors and their persisted policy state."""
    root = _database_root(install_root)
    with Database(root) as database:
        query = "SELECT * FROM spaces"
        parameters: tuple[Any, ...] = ()
        if not include_revoked:
            query += " WHERE status = 'active'"
        query += " ORDER BY kind, space_id"
        rows = database.conn.execute(query, parameters).fetchall()
    return [_space_row_to_dict(row) for row in rows]


def local_space_id(install_root: Union[str, Path]) -> str:
    """Return the active primary local Space for this install's Identity."""
    root = _database_root(install_root)
    with Database(root) as database:
        identity = database.conn.execute(
            "SELECT identity_id FROM identity LIMIT 1"
        ).fetchone()
        if identity is None:
            raise MembraneError("database has no local identity")
        row = database.conn.execute(
            """
            SELECT s.space_id
            FROM spaces s
            INNER JOIN space_memberships m ON m.space_id = s.space_id
            WHERE m.identity_id = ?
              AND m.primary_host = 1
              AND m.status = 'active'
              AND s.kind = 'local'
              AND s.status = 'active'
            ORDER BY s.space_id
            LIMIT 1
            """,
            (identity["identity_id"],),
        ).fetchone()
    if row is None:
        raise MembraneError("local Identity has no active primary Space membership")
    return str(row["space_id"])


def evaluate_space_access(
    install_root: Union[str, Path],
    *,
    space_id: str,
    identity_id: Optional[str] = None,
    capability: str,
) -> dict[str, Any]:
    """Return a deny-by-default decision for one Space capability."""
    _validate_identifier(space_id, "space_id")
    if capability not in SPACE_CAPABILITIES:
        raise MembraneError(
            f"capability must be one of {SPACE_CAPABILITIES}; got {capability!r}"
        )
    root = _database_root(install_root)
    with Database(root) as database:
        local_identity = database.conn.execute(
            "SELECT identity_id FROM identity LIMIT 1"
        ).fetchone()
        if local_identity is None:
            raise MembraneError("database has no local identity")
        effective_identity_id = identity_id or str(local_identity["identity_id"])
        space = database.conn.execute(
            "SELECT * FROM spaces WHERE space_id = ?",
            (space_id,),
        ).fetchone()
        if space is None:
            return _access_decision(space_id, capability, False, "unknown_space")
        policy = _policy_from_row(space)
        membership = database.conn.execute(
            """
            SELECT status, primary_host
            FROM space_memberships
            WHERE space_id = ? AND identity_id = ?
            """,
            (space_id, effective_identity_id),
        ).fetchone()
        active_member = (
            membership is not None
            and membership["status"] == "active"
            and space["status"] == "active"
        )

    if capability in {"surface", "interaction_signal"}:
        allowed = active_member
        reason = "active_membership" if allowed else "active_membership_required"
    elif capability == "public_card":
        allowed = bool(policy["known"] and policy["export_policy"]["public_card"])
        reason = "public_card_policy" if allowed else "public_card_denied"
    else:
        allowed = False
        reason = "private_geometry_denied"
    return _access_decision(space_id, capability, allowed, reason)


def require_space_access(
    install_root: Union[str, Path],
    *,
    space_id: str,
    identity_id: Optional[str] = None,
    capability: str,
) -> dict[str, Any]:
    """Raise unless the local membrane permits a capability."""
    decision = evaluate_space_access(
        install_root,
        space_id=space_id,
        identity_id=identity_id,
        capability=capability,
    )
    if not decision["allowed"]:
        raise MembraneError(
            f"Space access denied for {space_id!r}: {decision['reason']}"
        )
    return decision


def export_space_boundary(
    install_root: Union[str, Path],
    *,
    space_id: Optional[str] = None,
) -> dict[str, Any]:
    """Build a public descriptor without exporting private Identity geometry."""
    root = Path(install_root).expanduser().resolve()
    db_path = database_path(root)
    if not db_path.is_file():
        raise MembraneError(f"No IE database under {root}")

    with Database(db_path) as database:
        install = database.conn.execute("SELECT * FROM install LIMIT 1").fetchone()
        identity = database.conn.execute("SELECT * FROM identity LIMIT 1").fetchone()
        if install is None or identity is None:
            raise MembraneError("database has no local install and identity")
        effective_space_id = space_id or local_space_id(root)
        _validate_identifier(effective_space_id, "space_id")
        space = database.conn.execute(
            "SELECT * FROM spaces WHERE space_id = ? AND kind = 'local' AND status = 'active'",
            (effective_space_id,),
        ).fetchone()
        if space is None:
            raise MembraneError(f"local Space not found: {effective_space_id}")
        membership = database.conn.execute(
            """
            SELECT 1 FROM space_memberships
            WHERE space_id = ? AND identity_id = ? AND status = 'active'
            """,
            (effective_space_id, identity["identity_id"]),
        ).fetchone()
        if membership is None:
            raise MembraneError(
                f"local Identity is not an active member of Space: {effective_space_id}"
            )
        policy = _policy_from_row(space)
        payload = {
            "space": {
                "space_id": effective_space_id,
                "kind": str(space["kind"]),
                "hosting": str(space["hosting"]),
                "identity_id": str(space["sovereign_identity_id"]),
                "local_handle": str(space["local_handle"]),
                "preferred_name": space["preferred_name"],
                "substrate": str(space["substrate"]),
            },
            "membrane": policy,
        }

    checksum = sha256_text(canonical_json(payload))
    return {
        "format": MEMBRANE_FORMAT,
        "format_version": MEMBRANE_FORMAT_VERSION,
        "boundary_id": checksum,
        "payload_sha256": checksum,
        "payload": payload,
    }


def verify_space_boundary(document: Any) -> dict[str, Any]:
    """Validate a boundary descriptor without granting access to its Space."""
    if not isinstance(document, dict):
        raise MembraneError("Space boundary must be an object")
    required = {"format", "format_version", "boundary_id", "payload_sha256", "payload"}
    if set(document) != required:
        raise MembraneError("Space boundary envelope has unsupported fields")
    if document.get("format") != MEMBRANE_FORMAT:
        raise MembraneError("unsupported Space boundary format")
    if document.get("format_version") != MEMBRANE_FORMAT_VERSION:
        raise MembraneError("unsupported Space boundary version")
    payload = document.get("payload")
    if not isinstance(payload, dict) or set(payload) != {"space", "membrane"}:
        raise MembraneError("Space boundary payload is invalid")
    expected = sha256_text(canonical_json(payload))
    if document.get("payload_sha256") != expected or document.get("boundary_id") != expected:
        raise MembraneError("Space boundary checksum mismatch")

    space = payload["space"]
    membrane = payload["membrane"]
    if not isinstance(space, dict) or set(space) != {
        "space_id",
        "kind",
        "hosting",
        "identity_id",
        "local_handle",
        "preferred_name",
        "substrate",
    }:
        raise MembraneError("Space boundary identity descriptor is invalid")
    for field in ("space_id", "identity_id", "local_handle", "substrate"):
        _validate_identifier(space.get(field), f"space.{field}")
    if space.get("preferred_name") is not None and not isinstance(space["preferred_name"], str):
        raise MembraneError("space.preferred_name must be text or null")
    if space.get("kind") != "local" or space.get("hosting") != "local_device":
        raise MembraneError("unsupported Space boundary hosting")
    if not isinstance(membrane, dict) or set(membrane) != {
        "known",
        "addressable",
        "export_policy",
        "inbound_policy",
    }:
        raise MembraneError("Space membrane policy is invalid")
    if not isinstance(membrane["known"], bool) or not isinstance(membrane["addressable"], bool):
        raise MembraneError("Space membrane visibility flags are invalid")
    if membrane["known"] is not True or membrane["addressable"] is not False:
        raise MembraneError("Space boundary must be known but not addressable")
    if membrane["export_policy"] != {
        "public_card": True,
        "full_private_geometry": False,
    }:
        raise MembraneError("Space export policy is not membrane-safe")
    if membrane["inbound_policy"] != {
        "interaction_signals": "grant_and_membrane",
        "private_geometry": "deny",
    }:
        raise MembraneError("Space inbound policy is not membrane-safe")
    return document


def accept_inbound_boundary(
    document: Any,
    *,
    expected_space_id: Optional[str] = None,
    install_root: Optional[Union[str, Path]] = None,
) -> dict[str, Any]:
    """Classify and optionally persist a remote Space as known, never addressable."""
    verified = verify_space_boundary(document)
    space = verified["payload"]["space"]
    if expected_space_id is not None and space["space_id"] != expected_space_id:
        raise MembraneError("Space boundary does not match the expected Space")
    registered = False
    if install_root is not None:
        root = _database_root(install_root)
        now = utcnow()
        with Database(root) as database:
            local_identity = database.conn.execute(
                "SELECT identity_id FROM identity LIMIT 1"
            ).fetchone()
            if local_identity is None:
                raise MembraneError("database has no local identity")
            existing = database.conn.execute(
                "SELECT kind, sovereign_identity_id FROM spaces WHERE space_id = ?",
                (space["space_id"],),
            ).fetchone()
            if (
                existing is not None
                and existing["kind"] == "local"
                and existing["sovereign_identity_id"] != space["identity_id"]
            ):
                raise MembraneError("inbound Space collides with a local Space")
            with database.transaction() as connection:
                connection.execute(
                    """
                    INSERT INTO spaces(
                        space_id, kind, hosting, parent_space_id, sovereign_identity_id,
                        local_handle, preferred_name, substrate, boundary_id, policy_json,
                        known, addressable, status, created_at, updated_at
                    ) VALUES (?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, 1, 0, 'active', ?, ?)
                    ON CONFLICT(space_id) DO UPDATE SET
                        kind = excluded.kind,
                        hosting = excluded.hosting,
                        sovereign_identity_id = excluded.sovereign_identity_id,
                        local_handle = excluded.local_handle,
                        preferred_name = excluded.preferred_name,
                        substrate = excluded.substrate,
                        boundary_id = excluded.boundary_id,
                        policy_json = excluded.policy_json,
                        known = 1,
                        addressable = 0,
                        status = 'active',
                        updated_at = excluded.updated_at
                    """,
                    (
                        space["space_id"],
                        space["kind"],
                        space["hosting"],
                        space["identity_id"],
                        space["local_handle"],
                        space["preferred_name"],
                        space["substrate"],
                        verified["boundary_id"],
                        canonical_json(verified["payload"]["membrane"]),
                        now,
                        now,
                    ),
                )
        registered = True
    return {
        "status": "known",
        "space_id": space["space_id"],
        "identity_id": space["identity_id"],
        "local_handle": space["local_handle"],
        "addressable": False,
        "private_geometry_accepted": False,
        "boundary_id": verified["boundary_id"],
        "registered": registered,
    }


def write_space_boundary(
    install_root: Union[str, Path],
    destination: Union[str, Path],
    *,
    space_id: Optional[str] = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Write a public boundary descriptor as JSON."""
    destination_path = Path(destination).expanduser().resolve()
    if destination_path.exists() and not overwrite:
        raise DatabaseError(f"Space boundary destination already exists: {destination_path}")
    document = export_space_boundary(install_root, space_id=space_id)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    destination_path.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "destination": str(destination_path),
        "boundary_id": document["boundary_id"],
        "space_id": document["payload"]["space"]["space_id"],
        "private_geometry_exported": False,
    }


def _validate_identifier(value: Any, label: str) -> None:
    if not isinstance(value, str) or not 1 <= len(value) <= 128 or not value.strip():
        raise MembraneError(f"{label} is invalid")


def _database_root(install_root: Union[str, Path]) -> Path:
    root = Path(install_root).expanduser().resolve()
    if not database_path(root).is_file():
        raise MembraneError(f"No IE database under {root}")
    return root


def _policy_from_row(row: Any) -> dict[str, Any]:
    try:
        policy = json.loads(row["policy_json"])
    except (TypeError, json.JSONDecodeError) as exc:
        raise MembraneError("stored Space membrane policy is invalid JSON") from exc
    if not isinstance(policy, dict):
        raise MembraneError("stored Space membrane policy must be an object")
    _validate_policy(policy)
    return policy


def _validate_policy(policy: dict[str, Any]) -> None:
    if policy != DEFAULT_SPACE_MEMBRANE_POLICY:
        raise MembraneError("stored Space membrane policy is not membrane-safe")


def _space_row_to_dict(row: Any) -> dict[str, Any]:
    return {
        "space_id": row["space_id"],
        "kind": row["kind"],
        "hosting": row["hosting"],
        "parent_space_id": row["parent_space_id"],
        "sovereign_identity_id": row["sovereign_identity_id"],
        "local_handle": row["local_handle"],
        "preferred_name": row["preferred_name"],
        "substrate": row["substrate"],
        "boundary_id": row["boundary_id"],
        "policy": json.loads(row["policy_json"]),
        "known": bool(row["known"]),
        "addressable": bool(row["addressable"]),
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _access_decision(
    space_id: str,
    capability: str,
    allowed: bool,
    reason: str,
) -> dict[str, Any]:
    return {
        "space_id": space_id,
        "capability": capability,
        "allowed": allowed,
        "reason": reason,
    }