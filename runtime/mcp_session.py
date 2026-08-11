"""Identity-scoped session for local Surface MCP binding.

V1 binds the process to the single install Identity. There is no anonymous
account-root session and no silent elevation across Identities.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from .database import Database, database_path
from .membrane import local_space_id, require_space_access


@dataclass(frozen=True)
class IdentitySession:
    """Authenticated Surface session for one Identity in one install."""

    install_root: Path
    identity_id: str
    local_handle: str
    preferred_name: Optional[str]
    substrate: str
    space_id: Optional[str] = None

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

    def require_capability(self, capability: str) -> dict[str, Any]:
        """Re-check the bound Space before serving a tool request."""
        if self.space_id is None:
            raise RuntimeError("MCP session has no bound Space")
        return require_space_access(
            self.install_root,
            space_id=self.space_id,
            identity_id=self.identity_id,
            capability=capability,
        )


def bind_local_session(
    install_root: Path | str,
    *,
    space_id: Optional[str] = None,
) -> IdentitySession:
    """Bind MCP/HTTP session to the sole Identity and an active Space membership."""
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

    effective_space_id = space_id or local_space_id(root)
    require_space_access(
        root,
        space_id=effective_space_id,
        identity_id=str(row["identity_id"]),
        capability="surface",
    )

    return IdentitySession(
        install_root=root,
        identity_id=str(row["identity_id"]),
        local_handle=str(row["local_handle"]),
        preferred_name=row["preferred_name"],
        substrate=str(row["substrate"] or "human"),
        space_id=effective_space_id,
    )
