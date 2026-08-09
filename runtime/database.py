"""SQLite database lifecycle and the initial DB-only V1 schema."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional, Union
from uuid import uuid4

DB_DIR_NAME = ".ie"
DB_FILENAME = "ie.sqlite3"
SCHEMA_VERSION = 5


class DatabaseError(RuntimeError):
    """Raised when a local IE database cannot be opened or initialized."""


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_json(value: Any) -> str:
    """Serialize JSON fields deterministically for storage and hashing."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def database_path(install_root: Union[str, Path]) -> Path:
    return Path(install_root).expanduser().resolve() / DB_DIR_NAME / DB_FILENAME


def _resolve_database_path(path: Union[str, Path]) -> Path:
    candidate = Path(path).expanduser()
    if candidate.name == DB_FILENAME or candidate.suffix in {".db", ".sqlite", ".sqlite3"}:
        return candidate.resolve()
    return database_path(candidate)


INITIAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS install (
    install_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    account_mode TEXT NOT NULL DEFAULT 'no_account',
    account_id TEXT,
    tier TEXT NOT NULL DEFAULT 'free',
    app_version TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS identity (
    identity_id TEXT PRIMARY KEY,
    install_id TEXT NOT NULL UNIQUE REFERENCES install(install_id) ON DELETE CASCADE,
    local_handle TEXT NOT NULL UNIQUE,
    preferred_name TEXT,
    substrate TEXT NOT NULL,
    accepts_ie_signals INTEGER NOT NULL DEFAULT 1 CHECK (accepts_ie_signals IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_signal_at TEXT,
    last_mature_at TEXT
);

CREATE TABLE IF NOT EXISTS privacy_defaults (
    identity_id TEXT PRIMARY KEY REFERENCES identity(identity_id) ON DELETE CASCADE,
    share_existence INTEGER NOT NULL DEFAULT 1 CHECK (share_existence IN (0, 1)),
    share_interaction_depth_delta INTEGER NOT NULL DEFAULT 1 CHECK (share_interaction_depth_delta IN (0, 1)),
    share_sender_emergent_mass INTEGER NOT NULL DEFAULT 1 CHECK (share_sender_emergent_mass IN (0, 1)),
    share_sender_last_mature_at INTEGER NOT NULL DEFAULT 1 CHECK (share_sender_last_mature_at IN (0, 1)),
    share_coarse_mass_estimate INTEGER NOT NULL DEFAULT 0 CHECK (share_coarse_mass_estimate IN (0, 1)),
    share_dimensions_delta INTEGER NOT NULL DEFAULT 0 CHECK (share_dimensions_delta IN (0, 1)),
    share_relation_pull INTEGER NOT NULL DEFAULT 0 CHECK (share_relation_pull IN (0, 1)),
    share_rich_signals INTEGER NOT NULL DEFAULT 0 CHECK (share_rich_signals IN (0, 1)),
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS consent_grants (
    grant_id TEXT PRIMARY KEY,
    identity_id TEXT NOT NULL REFERENCES identity(identity_id) ON DELETE CASCADE,
    sender_handle TEXT NOT NULL,
    field_name TEXT NOT NULL,
    granted_at TEXT NOT NULL,
    revoked_at TEXT,
    source TEXT NOT NULL,
    note TEXT
);

CREATE INDEX IF NOT EXISTS idx_consent_grants_lookup
    ON consent_grants(identity_id, sender_handle, field_name, granted_at DESC);

CREATE TABLE IF NOT EXISTS quarantines (
    quarantine_id TEXT PRIMARY KEY,
    identity_id TEXT NOT NULL REFERENCES identity(identity_id) ON DELETE CASCADE,
    sender_handle TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL,
    revoked_at TEXT,
    source TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_quarantines_lookup
    ON quarantines(identity_id, sender_handle, active);

CREATE TABLE IF NOT EXISTS policy_events (
    policy_event_id TEXT PRIMARY KEY,
    identity_id TEXT NOT NULL REFERENCES identity(identity_id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    subject_handle TEXT,
    field_name TEXT,
    previous_value_json TEXT,
    new_value_json TEXT,
    actor TEXT NOT NULL,
    reason TEXT,
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS metric_dimensions (
    dimension_id TEXT PRIMARY KEY,
    identity_id TEXT NOT NULL REFERENCES identity(identity_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    weight REAL NOT NULL DEFAULT 1.0,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    discovered_via TEXT,
    first_seen TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(identity_id, name)
);

CREATE TABLE IF NOT EXISTS metric_pairs (
    pair_id TEXT PRIMARY KEY,
    identity_id TEXT NOT NULL REFERENCES identity(identity_id) ON DELETE CASCADE,
    dim_a_id TEXT NOT NULL REFERENCES metric_dimensions(dimension_id) ON DELETE CASCADE,
    dim_b_id TEXT NOT NULL REFERENCES metric_dimensions(dimension_id) ON DELETE CASCADE,
    g REAL NOT NULL,
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    source TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(identity_id, dim_a_id, dim_b_id),
    CHECK (dim_a_id <> dim_b_id)
);

CREATE TABLE IF NOT EXISTS registry_entries (
    entry_id TEXT PRIMARY KEY,
    identity_id TEXT NOT NULL REFERENCES identity(identity_id) ON DELETE CASCADE,
    peer_handle TEXT NOT NULL,
    preferred_name TEXT,
    substrate TEXT,
    description TEXT NOT NULL DEFAULT '',
    first_noticed TEXT NOT NULL,
    last_interaction TEXT,
    interaction_count INTEGER NOT NULL DEFAULT 0,
    interaction_depth REAL NOT NULL DEFAULT 0.0,
    my_mass_estimate REAL,
    mass_confidence REAL,
    estimate_updated_at TEXT,
    estimate_as_of_peer_mature_at TEXT,
    peer_last_mature_at TEXT,
    peer_last_mature_seen_at TEXT,
    recognition_json TEXT NOT NULL DEFAULT '{}',
    relation_json TEXT NOT NULL DEFAULT '{}',
    effect_on_me_json TEXT NOT NULL DEFAULT '{}',
    perceived_ownership_json TEXT NOT NULL DEFAULT '{}',
    privacy_json TEXT NOT NULL DEFAULT '{}',
    tags_json TEXT NOT NULL DEFAULT '[]',
    notes TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'manual',
    revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(identity_id, peer_handle)
);

CREATE TABLE IF NOT EXISTS registry_entry_revisions (
    revision_id TEXT PRIMARY KEY,
    entry_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    actor TEXT NOT NULL,
    event_id TEXT,
    mature_id TEXT,
    snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(entry_id, revision)
);

CREATE TABLE IF NOT EXISTS registry_dimension_values (
    entry_id TEXT NOT NULL REFERENCES registry_entries(entry_id) ON DELETE CASCADE,
    dimension_id TEXT NOT NULL REFERENCES metric_dimensions(dimension_id) ON DELETE CASCADE,
    value REAL NOT NULL,
    confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
    source TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    observed_at TEXT NOT NULL,
    revision INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY(entry_id, dimension_id)
);

CREATE TABLE IF NOT EXISTS registry_dimension_revisions (
    revision_id TEXT PRIMARY KEY,
    entry_id TEXT NOT NULL,
    dimension_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    actor TEXT NOT NULL,
    event_id TEXT,
    mature_id TEXT,
    snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(entry_id, dimension_id, revision)
);

CREATE TABLE IF NOT EXISTS interaction_events (
    event_id TEXT PRIMARY KEY,
    install_id TEXT NOT NULL REFERENCES install(install_id) ON DELETE CASCADE,
    from_handle TEXT NOT NULL,
    to_handle TEXT NOT NULL,
    signal_timestamp TEXT NOT NULL,
    received_at TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    transport TEXT NOT NULL,
    canonical_payload_json TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    in_reply_to_request_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_interaction_events_sender
    ON interaction_events(install_id, from_handle, signal_timestamp);

CREATE TABLE IF NOT EXISTS apply_receipts (
    receipt_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE REFERENCES interaction_events(event_id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('accepted', 'applied', 'partial', 'rejected')),
    timestamp TEXT NOT NULL,
    from_handle TEXT NOT NULL,
    to_handle TEXT NOT NULL,
    applied_fields_json TEXT NOT NULL DEFAULT '[]',
    rejected_fields_json TEXT NOT NULL DEFAULT '[]',
    reason TEXT NOT NULL DEFAULT '',
    quarantine INTEGER NOT NULL DEFAULT 0 CHECK (quarantine IN (0, 1))
);

CREATE TABLE IF NOT EXISTS foreign_estimates (
    identity_id TEXT NOT NULL REFERENCES identity(identity_id) ON DELETE CASCADE,
    sender_handle TEXT NOT NULL,
    sender_substrate TEXT,
    first_signal_at TEXT NOT NULL,
    last_signal_at TEXT NOT NULL,
    signal_count INTEGER NOT NULL DEFAULT 0,
    accumulated_depth REAL NOT NULL DEFAULT 0.0,
    last_depth_delta REAL NOT NULL DEFAULT 0.0,
    existence_confirmed INTEGER NOT NULL DEFAULT 0 CHECK (existence_confirmed IN (0, 1)),
    coarse_mass_estimate REAL,
    mass_confidence REAL,
    mass_estimate_at TEXT,
    dimensions_delta_json TEXT,
    relation_pull REAL,
    sender_emergent_mass REAL,
    sender_emergent_mass_at TEXT,
    sender_last_mature_at TEXT,
    sender_last_mature_seen_at TEXT,
    last_receipt_id TEXT,
    quarantine INTEGER NOT NULL DEFAULT 0 CHECK (quarantine IN (0, 1)),
    notes TEXT,
    PRIMARY KEY(identity_id, sender_handle)
);

CREATE TABLE IF NOT EXISTS estimate_requests (
    request_id TEXT PRIMARY KEY,
    identity_id TEXT NOT NULL REFERENCES identity(identity_id) ON DELETE CASCADE,
    direction TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    requester_handle TEXT NOT NULL,
    target_handle TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'ignored', 'quarantined', 'answered', 'expired')),
    requested_fields_json TEXT NOT NULL DEFAULT '[]',
    note TEXT,
    schema_version TEXT NOT NULL DEFAULT '0',
    transport TEXT NOT NULL DEFAULT 'cli',
    answered_at TEXT,
    reply_receipt_id TEXT,
    ignored_at TEXT,
    quarantine INTEGER NOT NULL DEFAULT 0 CHECK (quarantine IN (0, 1)),
    created_at TEXT NOT NULL,
    mature_id TEXT
);

CREATE INDEX IF NOT EXISTS idx_estimate_requests_status
    ON estimate_requests(identity_id, direction, status, timestamp);

CREATE TABLE IF NOT EXISTS evidence_sources (
    source_id TEXT PRIMARY KEY,
    identity_id TEXT NOT NULL REFERENCES identity(identity_id) ON DELETE CASCADE,
    source_kind TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    root_relative_path TEXT,
    byte_size INTEGER,
    observed_mtime TEXT,
    sha256 TEXT NOT NULL,
    snapshot_text TEXT,
    captured_at TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(identity_id, source_kind, source_ref, sha256)
);

CREATE TABLE IF NOT EXISTS stem_state (
    identity_id TEXT PRIMARY KEY REFERENCES identity(identity_id) ON DELETE CASCADE,
    revision INTEGER NOT NULL DEFAULT 1,
    state_differential_json TEXT NOT NULL DEFAULT '{}',
    vision_gradient_json TEXT NOT NULL DEFAULT '{}',
    coherence_json TEXT NOT NULL DEFAULT '{}',
    substance_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL,
    last_mature_id TEXT
);

CREATE TABLE IF NOT EXISTS stem_revisions (
    revision_id TEXT PRIMARY KEY,
    identity_id TEXT NOT NULL REFERENCES identity(identity_id) ON DELETE CASCADE,
    revision INTEGER NOT NULL,
    previous_revision INTEGER,
    mature_id TEXT,
    snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(identity_id, revision)
);

CREATE TABLE IF NOT EXISTS workspace_items (
    item_id TEXT PRIMARY KEY,
    identity_id TEXT NOT NULL REFERENCES identity(identity_id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('observation', 'hypothesis', 'decision', 'commitment', 'question', 'goal', 'note')),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    priority INTEGER,
    due_at TEXT,
    tags_json TEXT NOT NULL DEFAULT '[]',
    source_id TEXT,
    revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workspace_item_revisions (
    revision_id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    operation TEXT NOT NULL CHECK (operation IN ('create', 'update', 'complete', 'archive')),
    actor TEXT NOT NULL,
    mature_id TEXT,
    snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(item_id, revision)
);

CREATE TABLE IF NOT EXISTS geometry_receipts (
    receipt_id TEXT PRIMARY KEY,
    install_id TEXT NOT NULL REFERENCES install(install_id) ON DELETE CASCADE,
    timestamp TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('think', 'interact', 'mature')),
    observer TEXT NOT NULL,
    target TEXT NOT NULL,
    source_apply_receipt_id TEXT REFERENCES apply_receipts(receipt_id),
    mature_id TEXT,
    relative_mass_proxy_json TEXT,
    tension_components_json TEXT NOT NULL DEFAULT '[]',
    degrees_of_freedom_json TEXT,
    jurisdiction_shift_json TEXT,
    stem_differential_json TEXT,
    ownership_move_json TEXT,
    optionality_delta_json TEXT,
    notes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS geometry_receipt_sources (
    receipt_id TEXT NOT NULL REFERENCES geometry_receipts(receipt_id) ON DELETE CASCADE,
    source_kind TEXT NOT NULL,
    source_id TEXT NOT NULL,
    PRIMARY KEY(receipt_id, source_kind, source_id)
);

CREATE TABLE IF NOT EXISTS mature_events (
    mature_id TEXT PRIMARY KEY,
    identity_id TEXT NOT NULL REFERENCES identity(identity_id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    actor TEXT NOT NULL,
    notes TEXT NOT NULL DEFAULT '',
    requested_changes_json TEXT NOT NULL DEFAULT '{}',
    applied_changes_json TEXT NOT NULL DEFAULT '{}',
    source_count INTEGER NOT NULL DEFAULT 0,
    stem_before_revision INTEGER,
    stem_after_revision INTEGER,
    registry_change_count INTEGER NOT NULL DEFAULT 0,
    workspace_change_count INTEGER NOT NULL DEFAULT 0,
    reassessment_requests_json TEXT NOT NULL DEFAULT '[]',
    geometry_receipt_id TEXT REFERENCES geometry_receipts(receipt_id)
);

CREATE TABLE IF NOT EXISTS trajectory_entries (
    trajectory_id TEXT PRIMARY KEY,
    identity_id TEXT NOT NULL REFERENCES identity(identity_id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('interact', 'mature')),
    mature_id TEXT,
    geometry_receipt_id TEXT REFERENCES geometry_receipts(receipt_id),
    summary TEXT NOT NULL,
    previous_stem_revision INTEGER,
    current_stem_revision INTEGER,
    previous_registry_revision INTEGER,
    current_registry_revision INTEGER,
    previous_workspace_revision INTEGER,
    current_workspace_revision INTEGER,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);
"""

PROJECTION_HISTORY_MIGRATION = """
CREATE TABLE registry_entry_revisions_v2 (
    revision_id TEXT PRIMARY KEY,
    entry_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    actor TEXT NOT NULL,
    event_id TEXT,
    mature_id TEXT,
    snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(entry_id, revision)
);

INSERT INTO registry_entry_revisions_v2(
    revision_id, entry_id, revision, actor, event_id, mature_id,
    snapshot_json, created_at
)
SELECT revision_id, entry_id, revision, actor, event_id, mature_id,
       snapshot_json, created_at
FROM registry_entry_revisions;

DROP TABLE registry_entry_revisions;
ALTER TABLE registry_entry_revisions_v2 RENAME TO registry_entry_revisions;

CREATE TABLE workspace_item_revisions_v2 (
    revision_id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL,
    revision INTEGER NOT NULL,
    operation TEXT NOT NULL CHECK (operation IN ('create', 'update', 'complete', 'archive')),
    actor TEXT NOT NULL,
    mature_id TEXT,
    snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(item_id, revision)
);

INSERT INTO workspace_item_revisions_v2(
    revision_id, item_id, revision, operation, actor, mature_id,
    snapshot_json, created_at
)
SELECT revision_id, item_id, revision, operation, actor, mature_id,
       snapshot_json, created_at
FROM workspace_item_revisions;

DROP TABLE workspace_item_revisions;
ALTER TABLE workspace_item_revisions_v2 RENAME TO workspace_item_revisions;
"""

MANAGED_SYNC_QUEUE_MIGRATION = """
CREATE TABLE IF NOT EXISTS managed_sync_queue (
    queue_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE,
    stream TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    idempotency_key TEXT NOT NULL UNIQUE,
    payload_json TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    previous_cursor TEXT,
    cursor TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'retry', 'accepted', 'blocked')),
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    next_attempt_at TEXT NOT NULL,
    last_error TEXT,
    server_cursor TEXT,
    accepted_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_managed_sync_queue_due
    ON managed_sync_queue(status, next_attempt_at, created_at);

CREATE INDEX IF NOT EXISTS idx_managed_sync_queue_stream
    ON managed_sync_queue(stream, status, created_at);

CREATE TABLE IF NOT EXISTS managed_sync_state (
    stream TEXT PRIMARY KEY,
    client_cursor TEXT,
    server_cursor TEXT,
    updated_at TEXT NOT NULL
);
"""

MANAGED_SYNC_LEASE_MIGRATION = """
CREATE TABLE IF NOT EXISTS managed_sync_leases (
    queue_id TEXT PRIMARY KEY REFERENCES managed_sync_queue(queue_id) ON DELETE CASCADE,
    lease_id TEXT NOT NULL UNIQUE,
    lease_until TEXT NOT NULL,
    claimed_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_managed_sync_leases_expiry
    ON managed_sync_leases(lease_until);
"""

JURISDICTION_GRANTS_MIGRATION = """
-- Creator lineage (nullable for genesis / V1 bootstrap). No FK to keep V1 simple.
ALTER TABLE identity ADD COLUMN creator_identity_id TEXT;

CREATE TABLE IF NOT EXISTS identity_grants (
    grant_id TEXT PRIMARY KEY,
    actor_identity_id TEXT NOT NULL REFERENCES identity(identity_id),
    object_identity_id TEXT NOT NULL REFERENCES identity(identity_id),
    scope TEXT NOT NULL,
    residual INTEGER NOT NULL DEFAULT 0 CHECK (residual IN (0, 1)),
    transferable INTEGER NOT NULL DEFAULT 1 CHECK (transferable IN (0, 1)),
    space_id TEXT,
    granted_at TEXT NOT NULL,
    revoked_at TEXT,
    granted_by_identity_id TEXT REFERENCES identity(identity_id),
    note TEXT
);

CREATE INDEX IF NOT EXISTS idx_identity_grants_object
    ON identity_grants(object_identity_id, scope, revoked_at);

CREATE INDEX IF NOT EXISTS idx_identity_grants_actor
    ON identity_grants(actor_identity_id, scope, revoked_at);

-- Backfill self-owned default package for existing V1 identities (genesis residual on self).
-- UUID construction via randomblob is sufficient for one-time migration.
INSERT INTO identity_grants (
    grant_id, actor_identity_id, object_identity_id, scope, residual, transferable,
    space_id, granted_at, revoked_at, granted_by_identity_id, note
)
SELECT
    lower(hex(randomblob(4))) || '-' || lower(hex(randomblob(2))) || '-4' ||
    substr(lower(hex(randomblob(2))), 2) || '-' ||
    substr('89ab', abs(random()) % 4 + 1, 1) ||
    substr(lower(hex(randomblob(2))), 2) || '-' || lower(hex(randomblob(6))),
    i.identity_id,
    i.identity_id,
    s.scope,
    s.residual,
    s.transferable,
    NULL,
    i.created_at,
    NULL,
    i.identity_id,
    'v1-genesis-backfill'
FROM identity i
CROSS JOIN (
    SELECT 'policy_admin' AS scope, 0 AS residual, 1 AS transferable
    UNION ALL SELECT 'visibility_control', 0, 1
    UNION ALL SELECT 'surface_admin', 0, 1
    UNION ALL SELECT 'grant_admin', 0, 1
    UNION ALL SELECT 'residual_emergency', 1, 0
) AS s
WHERE NOT EXISTS (
    SELECT 1 FROM identity_grants g
    WHERE g.object_identity_id = i.identity_id AND g.scope = s.scope
);
"""

MIGRATIONS = (
    (1, "initial_db_only_v1", INITIAL_SCHEMA),
    (2, "preserve_projection_history", PROJECTION_HISTORY_MIGRATION),
    (3, "managed_sync_queue", MANAGED_SYNC_QUEUE_MIGRATION),
    (4, "managed_sync_leases", MANAGED_SYNC_LEASE_MIGRATION),
    (5, "jurisdiction_grants_and_lineage", JURISDICTION_GRANTS_MIGRATION),
)


def _chmod_private(path: Path, mode: int) -> None:
    try:
        path.chmod(mode)
    except OSError:
        pass


def connect_database(path: Union[str, Path]) -> sqlite3.Connection:
    db_path = _resolve_database_path(path)
    if not db_path.parent.exists():
        raise DatabaseError(f"Database directory does not exist: {db_path.parent}")
    connection = sqlite3.connect(str(db_path), timeout=5.0)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("PRAGMA synchronous = NORMAL")
    _chmod_private(db_path, 0o600)
    return connection


def migrate(connection: sqlite3.Connection) -> int:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            checksum TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )
        """
    )
    current = int(connection.execute("PRAGMA user_version").fetchone()[0])
    for version, name, sql in MIGRATIONS:
        if version <= current:
            continue
        checksum = sha256_text(sql)
        try:
            connection.executescript(
                "BEGIN IMMEDIATE;\n"
                + sql
                + "\nINSERT INTO schema_migrations(version, name, checksum, applied_at) "
                f"VALUES ({version}, {json.dumps(name)}, {json.dumps(checksum)}, {json.dumps(utcnow())});\n"
                f"PRAGMA user_version = {version};\nCOMMIT;"
            )
        except sqlite3.Error as exc:
            connection.rollback()
            raise DatabaseError(f"Migration {version} failed: {exc}") from exc
        current = version

    if current > SCHEMA_VERSION:
        raise DatabaseError(
            f"Database schema version {current} is newer than runtime {SCHEMA_VERSION}"
        )
    return current


class Database:
    """Connection wrapper with migration and explicit transaction helpers."""

    def __init__(self, path: Union[str, Path]):
        self.path = _resolve_database_path(path)
        self.connection: Optional[sqlite3.Connection] = None

    def __enter__(self) -> "Database":
        self.connection = connect_database(self.path)
        migrate(self.connection)
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self.connection is None:
            raise DatabaseError("database is not open")
        return self.connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            yield self.conn
        except Exception:
            self.conn.rollback()
            raise
        else:
            self.conn.commit()


def _issue_default_jurisdiction_package(
    connection: sqlite3.Connection,
    *,
    identity_id: str,
    granted_by_identity_id: str,
    granted_at: str,
    note: str = "creation-default",
) -> None:
    """Issue the locked default jurisdiction package (docs/identity-creation-jurisdiction.md)."""
    scopes = [
        ("policy_admin", 0, 1),
        ("visibility_control", 0, 1),
        ("surface_admin", 0, 1),
        ("grant_admin", 0, 1),
        ("residual_emergency", 1, 0),  # residual, non-transferable by ordinary revoke
    ]
    for scope, residual, transferable in scopes:
        connection.execute(
            """
            INSERT INTO identity_grants(
                grant_id, actor_identity_id, object_identity_id, scope, residual,
                transferable, space_id, granted_at, revoked_at, granted_by_identity_id, note
            ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?, NULL, ?, ?)
            """,
            (
                str(uuid4()),
                identity_id,  # V1 genesis: self holds the package
                identity_id,
                scope,
                residual,
                transferable,
                granted_at,
                granted_by_identity_id,
                note,
            ),
        )


def initialize_database(
    install_root: Union[str, Path],
    *,
    handle: str,
    preferred_name: Optional[str],
    substrate: str = "human",
    account_info: Optional[dict[str, Any]] = None,
    app_version: str = "",
) -> dict[str, str]:
    """Create a fresh DB-only install and return its stable metadata."""
    root = Path(install_root).expanduser().resolve()
    ie_dir = root / DB_DIR_NAME
    ie_dir.mkdir(parents=True, exist_ok=True)
    _chmod_private(ie_dir, 0o700)
    db_path = ie_dir / DB_FILENAME
    if db_path.exists():
        raise DatabaseError(
            f"IE database already exists at {db_path}; reset it explicitly first"
        )

    account_info = account_info or {}
    install_id = str(uuid4())
    identity_id = str(uuid4())
    now = utcnow()

    connection = connect_database(db_path)
    try:
        migrate(connection)
        with connection:
            connection.execute(
                """
                INSERT INTO install(
                    install_id, created_at, updated_at, account_mode, account_id,
                    tier, app_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    install_id,
                    now,
                    now,
                    account_info.get("account_mode") or "no_account",
                    account_info.get("account_id"),
                    account_info.get("tier") or "free",
                    app_version,
                ),
            )
            connection.execute(
                """
                INSERT INTO identity(
                    identity_id, install_id, local_handle, preferred_name, substrate,
                    accepts_ie_signals, created_at, updated_at, creator_identity_id
                ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, NULL)
                """,
                (identity_id, install_id, handle, preferred_name, substrate, now, now),
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
                """
                INSERT INTO stem_state(identity_id, revision, updated_at)
                VALUES (?, 1, ?)
                """,
                (identity_id, now),
            )
            for dimension_name in ("ownership_depth", "clarity_of_vision"):
                connection.execute(
                    """
                    INSERT INTO metric_dimensions(
                        dimension_id, identity_id, name, weight, active,
                        discovered_via, first_seen, note, revision, created_at, updated_at
                    ) VALUES (?, ?, ?, 1.0, 1, 'init', ?, '', 1, ?, ?)
                    """,
                    (str(uuid4()), identity_id, dimension_name, now, now, now),
                )
            # Creation-time default jurisdiction package (V1 genesis: self holds it)
            _issue_default_jurisdiction_package(
                connection,
                identity_id=identity_id,
                granted_by_identity_id=identity_id,
                granted_at=now,
                note="v1-genesis-creation",
            )
    finally:
        connection.close()
        _chmod_private(db_path, 0o600)

    return {
        "install_id": install_id,
        "identity_id": identity_id,
        "db_path": str(db_path),
    }


def database_info(path: Union[str, Path]) -> dict[str, Any]:
    db_path = _resolve_database_path(path)
    with Database(db_path) as database:
        conn = database.conn
        version = int(conn.execute("PRAGMA user_version").fetchone()[0])
        migration = conn.execute(
            "SELECT version, name, applied_at FROM schema_migrations ORDER BY version DESC LIMIT 1"
        ).fetchone()
        install = conn.execute(
            "SELECT install_id, created_at, updated_at, tier FROM install LIMIT 1"
        ).fetchone()
        table_count = int(
            conn.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchone()[0]
        )
        return {
            "path": str(db_path),
            "schema_version": version,
            "latest_migration": dict(migration) if migration else None,
            "install": dict(install) if install else None,
            "table_count": table_count,
            "journal_mode": str(conn.execute("PRAGMA journal_mode").fetchone()[0]),
            "foreign_keys": int(conn.execute("PRAGMA foreign_keys").fetchone()[0]),
        }


def database_integrity_check(path: Union[str, Path]) -> dict[str, Any]:
    """Run SQLite integrity and foreign-key checks without changing projections."""
    db_path = _resolve_database_path(path)
    with Database(db_path) as database:
        integrity_results = [
            row[0] for row in database.conn.execute("PRAGMA integrity_check").fetchall()
        ]
        foreign_key_violations = [
            dict(row) for row in database.conn.execute("PRAGMA foreign_key_check").fetchall()
        ]
    return {
        "path": str(db_path),
        "ok": integrity_results == ["ok"] and not foreign_key_violations,
        "integrity_check": integrity_results,
        "foreign_key_violations": foreign_key_violations,
    }


def backup_database(
    path: Union[str, Path],
    destination: Union[str, Path],
    *,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Create a consistent SQLite backup using the native online-backup API."""
    source_path = _resolve_database_path(path)
    if not source_path.is_file():
        raise DatabaseError(f"Database does not exist: {source_path}")
    destination_path = Path(destination).expanduser().resolve()
    if destination_path == source_path:
        raise DatabaseError("Backup destination must differ from the source database")
    if destination_path.exists() and not overwrite:
        raise DatabaseError(
            f"Backup destination already exists: {destination_path}; pass overwrite explicitly"
        )
    destination_path.parent.mkdir(parents=True, exist_ok=True)

    target = sqlite3.connect(str(destination_path))
    try:
        with Database(source_path) as database:
            database.conn.backup(target)
        target.commit()
    finally:
        target.close()
    _chmod_private(destination_path, 0o600)
    return {
        "source": str(source_path),
        "destination": str(destination_path),
        "bytes": destination_path.stat().st_size,
    }
