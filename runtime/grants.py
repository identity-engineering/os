"""Identity grants — list / revoke / transfer (creation-time jurisdiction package).

See docs/identity-creation-jurisdiction.md. Residual emergency grants are not
transferable and cannot be stripped by ordinary revoke.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union
from uuid import uuid4

from .context import ContextError, resolve_active_identity_row
from .database import Database, database_path, utcnow


class GrantError(RuntimeError):
    """Raised when a grant operation cannot complete."""


def _local_identity(conn) -> Any:
    try:
        return resolve_active_identity_row(conn)
    except ContextError as exc:
        raise GrantError(str(exc)) from exc


def _row_to_dict(row: Any) -> dict[str, Any]:
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
        "note": row["note"],
    }


def list_grants(
    install_root: Union[str, Path],
    *,
    active_only: bool = True,
) -> list[dict[str, Any]]:
    """List grants for the active Identity (as object)."""
    root = Path(install_root).expanduser().resolve()
    db_path = database_path(root)
    if not db_path.is_file():
        raise GrantError(f"No IE database under {root}")

    with Database(db_path) as database:
        identity = _local_identity(database.conn)
        if active_only:
            rows = database.conn.execute(
                """
                SELECT * FROM identity_grants
                WHERE object_identity_id = ? AND revoked_at IS NULL
                ORDER BY scope, granted_at
                """,
                (identity["identity_id"],),
            ).fetchall()
        else:
            rows = database.conn.execute(
                """
                SELECT * FROM identity_grants
                WHERE object_identity_id = ?
                ORDER BY scope, granted_at
                """,
                (identity["identity_id"],),
            ).fetchall()
    return [_row_to_dict(row) for row in rows]


def revoke_grant(
    install_root: Union[str, Path],
    *,
    grant_id: Optional[str] = None,
    scope: Optional[str] = None,
    reason: str = "",
) -> dict[str, Any]:
    """Revoke an ordinary (non-residual) active grant on the active Identity.

    Residual emergency grants cannot be revoked by this path.
    """
    if not grant_id and not scope:
        raise GrantError("pass --grant-id or --scope")

    root = Path(install_root).expanduser().resolve()
    db_path = database_path(root)
    if not db_path.is_file():
        raise GrantError(f"No IE database under {root}")

    now = utcnow()
    with Database(db_path) as database:
        with database.transaction() as conn:
            identity = _local_identity(conn)
            object_id = identity["identity_id"]

            if grant_id:
                row = conn.execute(
                    """
                    SELECT * FROM identity_grants
                    WHERE grant_id = ? AND object_identity_id = ?
                    """,
                    (grant_id, object_id),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT * FROM identity_grants
                    WHERE object_identity_id = ? AND scope = ? AND revoked_at IS NULL
                    ORDER BY granted_at DESC LIMIT 1
                    """,
                    (object_id, scope),
                ).fetchone()

            if row is None:
                raise GrantError("grant not found or already revoked")
            if row["revoked_at"]:
                raise GrantError(f"grant {row['grant_id']} already revoked")
            if int(row["residual"]):
                raise GrantError(
                    "residual emergency grant cannot be revoked by ordinary path"
                )

            note = row["note"] or ""
            if reason:
                note = (note + " | revoke: " + reason).strip(" |")

            conn.execute(
                """
                UPDATE identity_grants
                SET revoked_at = ?, note = ?
                WHERE grant_id = ?
                """,
                (now, note, row["grant_id"]),
            )

    return {
        "status": "revoked",
        "grant_id": row["grant_id"],
        "scope": row["scope"],
        "revoked_at": now,
        "reason": reason or None,
    }


def transfer_grant(
    install_root: Union[str, Path],
    *,
    to_actor_identity_id: str,
    grant_id: Optional[str] = None,
    scope: Optional[str] = None,
    reason: str = "",
) -> dict[str, Any]:
    """Transfer a transferable active grant to another actor Identity.

    Residual grants are never transferable. Target actor must exist in the
    local identity table (multi-Identity installs).
    """
    if not grant_id and not scope:
        raise GrantError("pass --grant-id or --scope")
    target = (to_actor_identity_id or "").strip()
    if not target:
        raise GrantError("--to-actor identity_id is required")

    root = Path(install_root).expanduser().resolve()
    db_path = database_path(root)
    if not db_path.is_file():
        raise GrantError(f"No IE database under {root}")

    now = utcnow()
    with Database(db_path) as database:
        with database.transaction() as conn:
            identity = _local_identity(conn)
            object_id = identity["identity_id"]

            target_row = conn.execute(
                "SELECT identity_id FROM identity WHERE identity_id = ?",
                (target,),
            ).fetchone()
            if target_row is None:
                raise GrantError(
                    f"target actor {target!r} not in local identity table "
                    "(multi-Identity required for real transfer)"
                )

            if grant_id:
                row = conn.execute(
                    """
                    SELECT * FROM identity_grants
                    WHERE grant_id = ? AND object_identity_id = ?
                    """,
                    (grant_id, object_id),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT * FROM identity_grants
                    WHERE object_identity_id = ? AND scope = ? AND revoked_at IS NULL
                    ORDER BY granted_at DESC LIMIT 1
                    """,
                    (object_id, scope),
                ).fetchone()

            if row is None:
                raise GrantError("grant not found or already revoked")
            if row["revoked_at"]:
                raise GrantError(f"grant {row['grant_id']} already revoked")
            if int(row["residual"]) or not int(row["transferable"]):
                raise GrantError(
                    "grant is residual or non-transferable; cannot transfer"
                )
            if row["actor_identity_id"] == target:
                raise GrantError("target actor already holds this grant")

            # Soft-revoke old grant; issue new grant to target (audit chain)
            old_note = row["note"] or ""
            revoke_note = (old_note + " | transferred_to: " + target).strip(" |")
            if reason:
                revoke_note = (revoke_note + " | " + reason).strip(" |")

            conn.execute(
                """
                UPDATE identity_grants
                SET revoked_at = ?, note = ?
                WHERE grant_id = ?
                """,
                (now, revoke_note, row["grant_id"]),
            )

            new_id = str(uuid4())
            conn.execute(
                """
                INSERT INTO identity_grants(
                    grant_id, actor_identity_id, object_identity_id, scope,
                    residual, transferable, space_id, granted_at, revoked_at,
                    granted_by_identity_id, note
                ) VALUES (?, ?, ?, ?, 0, 1, ?, ?, NULL, ?, ?)
                """,
                (
                    new_id,
                    target,
                    object_id,
                    row["scope"],
                    row["space_id"],
                    now,
                    identity["identity_id"],
                    f"transferred from {row['grant_id']}"
                    + (f": {reason}" if reason else ""),
                ),
            )

    return {
        "status": "transferred",
        "previous_grant_id": row["grant_id"],
        "new_grant_id": new_id,
        "scope": row["scope"],
        "to_actor_identity_id": target,
        "transferred_at": now,
        "reason": reason or None,
    }
