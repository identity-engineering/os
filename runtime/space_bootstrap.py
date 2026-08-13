"""Local Space + multi-Identity bootstrap helpers (OS #77)."""

from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

from .database import utcnow


def ensure_local_space_for_identity(
    connection,
    *,
    install_id: str,
    identity_id: str,
    created_at: Optional[str] = None,
) -> str:
    """Ensure a local mini-Space exists and the Identity is primary member.

    Returns space_id. Idempotent for the Identity's primary membership.
    """
    now = created_at or utcnow()
    existing = connection.execute(
        """
        SELECT m.space_id FROM space_memberships m
        JOIN spaces s ON s.space_id = m.space_id
        WHERE m.identity_id = ? AND m.primary_host = 1 AND m.status = 'active'
        LIMIT 1
        """,
        (identity_id,),
    ).fetchone()
    if existing is not None:
        return existing[0] if not hasattr(existing, "keys") else existing["space_id"]

    space_row = connection.execute(
        """
        SELECT space_id FROM spaces WHERE kind = 'local' ORDER BY created_at ASC LIMIT 1
        """
    ).fetchone()
    if space_row is None:
        space_id = str(uuid4())
        connection.execute(
            """
            INSERT INTO spaces(
                space_id, kind, hosting, parent_space_id, policy_json, created_at, updated_at
            ) VALUES (?, 'local', 'local_device', NULL, '{}', ?, ?)
            """,
            (space_id, now, now),
        )
    else:
        space_id = space_row[0] if not hasattr(space_row, "keys") else space_row["space_id"]

    connection.execute(
        """
        INSERT OR IGNORE INTO space_memberships(
            space_id, identity_id, primary_host, status, joined_at, revoked_at
        ) VALUES (?, ?, 1, 'active', ?, NULL)
        """,
        (space_id, identity_id, now),
    )
    connection.execute(
        """
        UPDATE install SET active_identity_id = COALESCE(active_identity_id, ?),
                           updated_at = ?
        WHERE install_id = ?
        """,
        (identity_id, now, install_id),
    )
    return space_id


def apply_local_space_multi_identity_migration(connection) -> None:
    """Schema v8: spaces, memberships, N identities per install, active_identity."""
    connection.execute("PRAGMA foreign_keys = OFF")

    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS spaces (
            space_id TEXT PRIMARY KEY,
            kind TEXT NOT NULL CHECK (kind IN ('local', 'ie_managed', 'governed')),
            hosting TEXT NOT NULL CHECK (hosting IN ('local_device', 'ie_federated', 'self')),
            parent_space_id TEXT,
            policy_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS space_memberships (
            space_id TEXT NOT NULL,
            identity_id TEXT NOT NULL,
            primary_host INTEGER NOT NULL DEFAULT 0 CHECK (primary_host IN (0, 1)),
            status TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'revoked', 'invited')),
            joined_at TEXT NOT NULL,
            revoked_at TEXT,
            PRIMARY KEY (space_id, identity_id)
        );

        CREATE INDEX IF NOT EXISTS idx_space_memberships_identity
            ON space_memberships(identity_id, primary_host, status);
        """
    )

    # active_identity_id on install (ignore if present)
    cols = {
        row[1]
        for row in connection.execute("PRAGMA table_info(install)").fetchall()
    }
    if "active_identity_id" not in cols:
        connection.execute("ALTER TABLE install ADD COLUMN active_identity_id TEXT")

    # Rebuild identity without UNIQUE(install_id) if still present
    create_sql = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='identity'"
    ).fetchone()
    needs_rebuild = create_sql is not None and "install_id TEXT NOT NULL UNIQUE" in (
        create_sql[0] or ""
    )
    if needs_rebuild:
        connection.executescript(
            """
            CREATE TABLE identity_v8 (
                identity_id TEXT PRIMARY KEY,
                install_id TEXT NOT NULL,
                local_handle TEXT NOT NULL UNIQUE,
                preferred_name TEXT,
                substrate TEXT NOT NULL,
                accepts_ie_signals INTEGER NOT NULL DEFAULT 1
                    CHECK (accepts_ie_signals IN (0, 1)),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_signal_at TEXT,
                last_mature_at TEXT,
                creator_identity_id TEXT
            );

            INSERT INTO identity_v8(
                identity_id, install_id, local_handle, preferred_name, substrate,
                accepts_ie_signals, created_at, updated_at, last_signal_at,
                last_mature_at, creator_identity_id
            )
            SELECT identity_id, install_id, local_handle, preferred_name, substrate,
                   accepts_ie_signals, created_at, updated_at, last_signal_at,
                   last_mature_at, creator_identity_id
            FROM identity;

            DROP TABLE identity;
            ALTER TABLE identity_v8 RENAME TO identity;
            """
        )

    # Backfill active identity + local space memberships
    for install in connection.execute("SELECT * FROM install").fetchall():
        install_id = install["install_id"]
        identities = connection.execute(
            """
            SELECT identity_id, created_at FROM identity
            WHERE install_id = ? ORDER BY created_at ASC
            """,
            (install_id,),
        ).fetchall()
        if not identities:
            continue
        first = identities[0]
        if not install["active_identity_id"]:
            connection.execute(
                "UPDATE install SET active_identity_id = ? WHERE install_id = ?",
                (first["identity_id"], install_id),
            )
        for ident in identities:
            ensure_local_space_for_identity(
                connection,
                install_id=install_id,
                identity_id=ident["identity_id"],
                created_at=ident["created_at"],
            )

    connection.execute("PRAGMA foreign_keys = ON")


def create_additional_identity(
    connection,
    *,
    install_id: str,
    handle: str,
    preferred_name: Optional[str],
    substrate: str = "human",
    creator_identity_id: Optional[str] = None,
) -> dict[str, Any]:
    """Create another Identity in an existing install (same local Space)."""
    from .database import _issue_default_jurisdiction_package

    now = utcnow()
    identity_id = str(uuid4())
    creator = creator_identity_id
    if creator is None:
        row = connection.execute(
            "SELECT identity_id FROM identity WHERE install_id = ? ORDER BY created_at LIMIT 1",
            (install_id,),
        ).fetchone()
        creator = row["identity_id"] if row else identity_id

    connection.execute(
        """
        INSERT INTO identity(
            identity_id, install_id, local_handle, preferred_name, substrate,
            accepts_ie_signals, created_at, updated_at, creator_identity_id
        ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
        """,
        (
            identity_id,
            install_id,
            handle,
            preferred_name,
            substrate,
            now,
            now,
            creator,
        ),
    )
    connection.execute(
        """
        INSERT INTO privacy_defaults(
            identity_id, share_existence, share_interaction_depth_delta,
            share_sender_emergent_mass, share_sender_last_mature_at,
            share_coarse_mass_estimate, share_dimensions_delta,
            share_relation_pull, share_rich_signals, updated_at
        ) VALUES (?, 1, 1, 1, 1, 0, 0, 0, 0, ?)
        """,
        (identity_id, now),
    )
    connection.execute(
        "INSERT INTO stem_state(identity_id, revision, updated_at) VALUES (?, 1, ?)",
        (identity_id, now),
    )
    for dimension_name in ("ownership_depth", "clarity_of_vision"):
        connection.execute(
            """
            INSERT INTO metric_dimensions(
                dimension_id, identity_id, name, weight, active,
                discovered_via, first_seen, note, revision, created_at, updated_at
            ) VALUES (?, ?, ?, 1.0, 1, 'identity_create', ?, '', 1, ?, ?)
            """,
            (str(uuid4()), identity_id, dimension_name, now, now, now),
        )
    _issue_default_jurisdiction_package(
        connection,
        identity_id=identity_id,
        granted_by_identity_id=creator,
        granted_at=now,
        note="additional-identity-creation",
    )
    space_id = ensure_local_space_for_identity(
        connection,
        install_id=install_id,
        identity_id=identity_id,
        created_at=now,
    )
    return {
        "identity_id": identity_id,
        "local_handle": handle,
        "preferred_name": preferred_name,
        "substrate": substrate,
        "creator_identity_id": creator,
        "space_id": space_id,
        "created_at": now,
    }
