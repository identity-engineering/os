"""Active Identity + Space context for a local install (OS #77)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional, Union

from .database import Database, database_path


class ContextError(RuntimeError):
    """Raised when active Identity/Space cannot be resolved."""


def _db(install_root: Union[str, Path]) -> Path:
    root = Path(install_root).expanduser().resolve()
    path = database_path(root)
    if not path.is_file():
        raise ContextError(f"No IE database under {root}")
    return path


def list_identities(install_root: Union[str, Path]) -> list[dict[str, Any]]:
    """All Identities in this install."""
    with Database(_db(install_root)) as database:
        rows = database.conn.execute(
            """
            SELECT identity_id, local_handle, preferred_name, substrate,
                   created_at, updated_at
            FROM identity
            ORDER BY created_at
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_active_identity(install_root: Union[str, Path]) -> dict[str, Any]:
    """Resolve the active Identity for this install.

    Prefer install.active_identity_id when set and valid; else the sole Identity
    or the oldest Identity.
    """
    with Database(_db(install_root)) as database:
        conn = database.conn
        install = conn.execute("SELECT * FROM install LIMIT 1").fetchone()
        if install is None:
            raise ContextError("no install row")

        active_id = None
        try:
            active_id = install["active_identity_id"]
        except (KeyError, IndexError):
            active_id = None

        row = None
        if active_id:
            row = conn.execute(
                "SELECT * FROM identity WHERE identity_id = ?",
                (active_id,),
            ).fetchone()
        if row is None:
            row = conn.execute(
                "SELECT * FROM identity ORDER BY created_at ASC LIMIT 1"
            ).fetchone()
        if row is None:
            raise ContextError("no local identity in database")
        return dict(row)


def set_active_identity(
    install_root: Union[str, Path],
    *,
    identity_id: Optional[str] = None,
    handle: Optional[str] = None,
) -> dict[str, Any]:
    """Set active Identity by id or local_handle."""
    if not identity_id and not handle:
        raise ContextError("pass identity_id or handle")

    with Database(_db(install_root)) as database:
        with database.transaction() as conn:
            if identity_id:
                row = conn.execute(
                    "SELECT * FROM identity WHERE identity_id = ?",
                    (identity_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM identity WHERE local_handle = ?",
                    (handle.strip(),),
                ).fetchone()
            if row is None:
                raise ContextError("identity not found in this install")
            from .database import utcnow

            now = utcnow()
            conn.execute(
                "UPDATE install SET active_identity_id = ?, updated_at = ?",
                (row["identity_id"], now),
            )
    return dict(row)


def list_spaces(install_root: Union[str, Path]) -> list[dict[str, Any]]:
    """Spaces known to this install (local v0: usually one mini-Space)."""
    with Database(_db(install_root)) as database:
        try:
            rows = database.conn.execute(
                """
                SELECT space_id, kind, hosting, parent_space_id, policy_json,
                       created_at, updated_at
                FROM spaces
                ORDER BY created_at
                """
            ).fetchall()
        except Exception as exc:
            raise ContextError(f"spaces table unavailable: {exc}") from exc
    return [dict(row) for row in rows]


def get_primary_space_for_identity(
    install_root: Union[str, Path],
    identity_id: str,
) -> Optional[dict[str, Any]]:
    """Return the primary-host Space membership + space row for an Identity."""
    with Database(_db(install_root)) as database:
        row = database.conn.execute(
            """
            SELECT s.*, m.primary_host, m.status AS membership_status
            FROM space_memberships m
            JOIN spaces s ON s.space_id = m.space_id
            WHERE m.identity_id = ? AND m.primary_host = 1 AND m.status = 'active'
            LIMIT 1
            """,
            (identity_id,),
        ).fetchone()
    return dict(row) if row else None
