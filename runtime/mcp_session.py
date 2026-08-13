"""Identity-scoped session for local Surface MCP binding.

Binds the process to one Identity in the install (default: active).
Optional identity_id / handle selects a non-active local Identity for the
session without requiring install.active_identity_id to change. No anonymous
account-root session and no silent elevation across Identities.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .context import ContextError, resolve_active_identity_row
from .database import Database, database_path


@dataclass(frozen=True)
class IdentitySession:
    """Authenticated Surface session for one Identity in one install."""

    install_root: Path
    identity_id: str
    local_handle: str
    preferred_name: Optional[str]
    substrate: str
    space_id: Optional[str] = None  # primary local Space when available

    def actor_envelope(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "actor_identity_id": self.identity_id,
            "local_handle": self.local_handle,
            "substrate": self.substrate,
        }
        if self.preferred_name:
            out["preferred_name"] = self.preferred_name
        if self.space_id is not None:
            out["space_id"] = self.space_id
        return out

    def with_actor(self, payload: dict[str, Any]) -> dict[str, Any]:
        merged = dict(payload)
        merged["actor"] = self.actor_envelope()
        return merged


def _resolve_space_id(conn, identity_id: str, space_id: Optional[str]) -> Optional[str]:
    if space_id is not None:
        return space_id
    try:
        space_row = conn.execute(
            """
            SELECT m.space_id FROM space_memberships m
            WHERE m.identity_id = ? AND m.primary_host = 1 AND m.status = 'active'
            LIMIT 1
            """,
            (identity_id,),
        ).fetchone()
        if space_row is not None:
            return str(space_row["space_id"])
    except Exception:
        return None
    return None


def bind_local_session(
    install_root: Path | str,
    *,
    space_id: Optional[str] = None,
    identity_id: Optional[str] = None,
    handle: Optional[str] = None,
) -> IdentitySession:
    """Bind MCP/HTTP session to one Identity in the install.

    Default: install active Identity. Pass identity_id or handle to bind a
    different local Identity for this process only (does not mutate
    install.active_identity_id).
    """
    if identity_id and handle:
        raise ValueError("pass only one of identity_id or handle")

    root = Path(install_root).expanduser().resolve()
    db_path = database_path(root)
    if not db_path.is_file():
        raise FileNotFoundError(f"No IE database under {root} (.ie/ie.sqlite3)")

    with Database(db_path) as database:
        conn = database.conn
        row = None
        if identity_id:
            row = conn.execute(
                "SELECT * FROM identity WHERE identity_id = ?",
                (identity_id.strip(),),
            ).fetchone()
            if row is None:
                raise RuntimeError(
                    f"identity_id not found in this install: {identity_id!r}"
                )
        elif handle:
            row = conn.execute(
                "SELECT * FROM identity WHERE local_handle = ?",
                (handle.strip(),),
            ).fetchone()
            if row is None:
                raise RuntimeError(
                    f"handle not found in this install: {handle!r}"
                )
        else:
            try:
                row = resolve_active_identity_row(conn)
            except ContextError as exc:
                raise RuntimeError(
                    f"IE database has no local identity: {db_path}"
                ) from exc

        resolved_space = _resolve_space_id(conn, str(row["identity_id"]), space_id)

    return IdentitySession(
        install_root=root,
        identity_id=str(row["identity_id"]),
        local_handle=str(row["local_handle"]),
        preferred_name=row["preferred_name"],
        substrate=str(row["substrate"] or "human"),
        space_id=resolved_space,
    )
