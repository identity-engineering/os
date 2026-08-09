"""Identity-scoped session for local Surface MCP binding.

V1 binds the process to the single install Identity. There is no anonymous
account-root session and no silent elevation across Identities.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .database import Database, database_path


@dataclass(frozen=True)
class IdentitySession:
    """Authenticated Surface session for one Identity in one install."""

    install_root: Path
    identity_id: str
    local_handle: str
    preferred_name: Optional[str]
    substrate: str
    space_id: Optional[str] = None  # reserved; membrane not enforced in local V1

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
    """Bind MCP/HTTP session to the install's sole Identity (V1)."""
    root = Path(install_root).expanduser().resolve()
    db_path = database_path(root)
    if not db_path.is_file():
        raise FileNotFoundError(f"No IE database under {root} (.ie/ie.sqlite3)")

    with Database(db_path) as database:
        row = database.conn.execute(
            """
            SELECT identity_id, local_handle, preferred_name, substrate
            FROM identity
            LIMIT 1
            """
        ).fetchone()
        if row is None:
            raise RuntimeError(f"IE database has no local identity: {db_path}")
        count = int(database.conn.execute("SELECT COUNT(*) FROM identity").fetchone()[0])
        if count != 1:
            raise RuntimeError(
                f"Local V1 MCP expects exactly one Identity per install; found {count}"
            )

    return IdentitySession(
        install_root=root,
        identity_id=str(row["identity_id"]),
        local_handle=str(row["local_handle"]),
        preferred_name=row["preferred_name"],
        substrate=str(row["substrate"] or "human"),
        space_id=space_id,
    )
