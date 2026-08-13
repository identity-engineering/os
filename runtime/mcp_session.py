"""Identity-scoped session for local Surface MCP binding.

Binds the process to the install's *active* Identity (OS #77). No anonymous
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


def bind_local_session(
    install_root: Path | str,
    *,
    space_id: Optional[str] = None,
) -> IdentitySession:
    """Bind MCP/HTTP session to the install's active Identity."""
    root = Path(install_root).expanduser().resolve()
    db_path = database_path(root)
    if not db_path.is_file():
        raise FileNotFoundError(f"No IE database under {root} (.ie/ie.sqlite3)")

    with Database(db_path) as database:
        try:
            row = resolve_active_identity_row(database.conn)
        except ContextError as exc:
            raise RuntimeError(f"IE database has no local identity: {db_path}") from exc

        resolved_space = space_id
        if resolved_space is None:
            try:
                space_row = database.conn.execute(
                    """
                    SELECT m.space_id FROM space_memberships m
                    WHERE m.identity_id = ? AND m.primary_host = 1 AND m.status = 'active'
                    LIMIT 1
                    """,
                    (row["identity_id"],),
                ).fetchone()
                if space_row is not None:
                    resolved_space = str(space_row["space_id"])
            except Exception:
                resolved_space = None

    return IdentitySession(
        install_root=root,
        identity_id=str(row["identity_id"]),
        local_handle=str(row["local_handle"]),
        preferred_name=row["preferred_name"],
        substrate=str(row["substrate"] or "human"),
        space_id=resolved_space,
    )
