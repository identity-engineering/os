"""Focused tests for the SQLite-first V1 database lifecycle."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from typer.testing import CliRunner

from ie.cli import app
from runtime.database import (
    Database,
    backup_database,
    database_info,
    database_integrity_check,
    initialize_database,
)


class DatabaseLifecycleTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "install"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_initialize_creates_private_db_and_seed_state(self):
        metadata = initialize_database(
            self.root,
            handle="me",
            preferred_name="Me",
            account_info={"account_mode": "no_account", "tier": "free"},
        )
        db_path = self.root / ".ie" / "ie.sqlite3"
        self.assertTrue(db_path.is_file())
        self.assertEqual(metadata["db_path"], str(db_path))

        with Database(db_path) as database:
            connection = database.conn
            self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            self.assertEqual(connection.execute("PRAGMA journal_mode").fetchone()[0], "wal")
            identity = connection.execute(
                "SELECT local_handle, preferred_name, creator_identity_id FROM identity"
            ).fetchone()
            self.assertEqual(
                dict(identity),
                {"local_handle": "me", "preferred_name": "Me", "creator_identity_id": None},
            )
            dimensions = connection.execute(
                "SELECT name FROM metric_dimensions ORDER BY name"
            ).fetchall()
            self.assertEqual([row[0] for row in dimensions], ["clarity_of_vision", "ownership_depth"])

            grants = connection.execute(
                "SELECT scope, residual, transferable FROM identity_grants ORDER BY scope"
            ).fetchall()
            scopes = {row["scope"]: (row["residual"], row["transferable"]) for row in grants}
            self.assertEqual(
                scopes,
                {
                    "grant_admin": (0, 1),
                    "policy_admin": (0, 1),
                    "residual_emergency": (1, 0),
                    "surface_admin": (0, 1),
                    "visibility_control": (0, 1),
                },
            )

            # Migration 6: profiles table exists
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            self.assertIn("access_jurisdiction_profiles", tables)

        info = database_info(db_path)
        self.assertEqual(info["schema_version"], 6)
        self.assertEqual(info["foreign_keys"], 1)
        self.assertEqual(info["journal_mode"], "wal")
        self.assertGreaterEqual(info["table_count"], 22)
        with Database(db_path) as database:
            for table in ("registry_entry_revisions", "workspace_item_revisions"):
                self.assertEqual(
                    database.conn.execute(f"PRAGMA foreign_key_list({table})").fetchall(),
                    [],
                )

    def test_reopen_preserves_data_and_migration_is_idempotent(self):
        initialize_database(self.root, handle="me", preferred_name="Me")
        db_path = self.root / ".ie" / "ie.sqlite3"

        with Database(db_path) as database:
            with database.transaction():
                database.conn.execute(
                    "INSERT INTO workspace_items(item_id, identity_id, kind, title, content, created_at, updated_at) "
                    "SELECT 'item-1', identity_id, 'note', 'A', 'B', '2026-08-08T00:00:00+00:00', '2026-08-08T00:00:00+00:00' "
                    "FROM identity"
                )

        with Database(db_path) as database:
            row = database.conn.execute(
                "SELECT title, content FROM workspace_items WHERE item_id = 'item-1'"
            ).fetchone()
            self.assertEqual(dict(row), {"title": "A", "content": "B"})
            migrations = database.conn.execute(
                "SELECT version, name FROM schema_migrations"
            ).fetchall()
            self.assertEqual(
                [tuple(row) for row in migrations],
                [
                    (1, "initial_db_only_v1"),
                    (2, "preserve_projection_history"),
                    (3, "managed_sync_queue"),
                    (4, "managed_sync_leases"),
                    (5, "jurisdiction_grants_and_lineage"),
                    (6, "access_jurisdiction_profiles"),
                ],
            )

    def test_v1_projection_history_survives_v2_migration(self):
        db_path = self.root / ".ie" / "ie.sqlite3"
        db_path.parent.mkdir(parents=True)
        connection = sqlite3.connect(str(db_path))
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(
            """
            CREATE TABLE install (
                install_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE identity (
                identity_id TEXT PRIMARY KEY,
                install_id TEXT NOT NULL,
                local_handle TEXT NOT NULL,
                preferred_name TEXT,
                substrate TEXT NOT NULL,
                accepts_ie_signals INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE registry_entries (
                entry_id TEXT PRIMARY KEY
            );
            CREATE TABLE workspace_items (
                item_id TEXT PRIMARY KEY
            );
            CREATE TABLE registry_entry_revisions (
                revision_id TEXT PRIMARY KEY,
                entry_id TEXT NOT NULL REFERENCES registry_entries(entry_id) ON DELETE CASCADE,
                revision INTEGER NOT NULL,
                actor TEXT NOT NULL,
                event_id TEXT,
                mature_id TEXT,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(entry_id, revision)
            );
            CREATE TABLE workspace_item_revisions (
                revision_id TEXT PRIMARY KEY,
                item_id TEXT NOT NULL REFERENCES workspace_items(item_id) ON DELETE CASCADE,
                revision INTEGER NOT NULL,
                operation TEXT NOT NULL CHECK (operation IN ('create', 'update', 'complete', 'archive')),
                actor TEXT NOT NULL,
                mature_id TEXT,
                snapshot_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(item_id, revision)
            );
            CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                checksum TEXT NOT NULL,
                applied_at TEXT NOT NULL
            );
            """
        )
        connection.execute("PRAGMA user_version = 1")
        connection.execute(
            "INSERT INTO install(install_id, created_at, updated_at) VALUES (?, ?, ?)",
            ("install-1", "2026-08-08T00:00:00+00:00", "2026-08-08T00:00:00+00:00"),
        )
        connection.execute(
            "INSERT INTO identity(identity_id, install_id, local_handle, preferred_name, substrate, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("id-1", "install-1", "me", "Me", "human", "2026-08-08T00:00:00+00:00", "2026-08-08T00:00:00+00:00"),
        )
        connection.execute(
            "INSERT INTO registry_entries(entry_id) VALUES (?)", ("entry-1",)
        )
        connection.execute(
            "INSERT INTO workspace_items(item_id) VALUES (?)", ("item-1",)
        )
        connection.execute(
            """
            INSERT INTO registry_entry_revisions(
                revision_id, entry_id, revision, actor, snapshot_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                "registry-revision-1",
                "entry-1",
                1,
                "legacy",
                '{"peer_handle":"alice"}',
                "2026-08-08T00:00:00+00:00",
            ),
        )
        connection.execute(
            """
            INSERT INTO workspace_item_revisions(
                revision_id, item_id, revision, operation, actor, snapshot_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "workspace-revision-1",
                "item-1",
                1,
                "create",
                "legacy",
                '{"title":"A"}',
                "2026-08-08T00:00:00+00:00",
            ),
        )
        connection.execute(
            "INSERT INTO schema_migrations(version, name, checksum, applied_at) VALUES (?, ?, ?, ?)",
            (1, "initial_db_only_v1", "legacy", "2026-08-08T00:00:00+00:00"),
        )
        connection.commit()
        connection.close()

        with Database(db_path) as database:
            registry_revision = database.conn.execute(
                "SELECT revision_id, entry_id, snapshot_json FROM registry_entry_revisions"
            ).fetchone()
            workspace_revision = database.conn.execute(
                "SELECT revision_id, item_id, snapshot_json FROM workspace_item_revisions"
            ).fetchone()
            self.assertEqual(
                tuple(registry_revision),
                ("registry-revision-1", "entry-1", '{"peer_handle":"alice"}'),
            )
            self.assertEqual(
                tuple(workspace_revision),
                ("workspace-revision-1", "item-1", '{"title":"A"}'),
            )
            for table in ("registry_entry_revisions", "workspace_item_revisions"):
                self.assertEqual(
                    database.conn.execute(f"PRAGMA foreign_key_list({table})").fetchall(),
                    [],
                )

            database.conn.execute("DELETE FROM registry_entries WHERE entry_id = 'entry-1'")
            database.conn.execute("DELETE FROM workspace_items WHERE item_id = 'item-1'")
            self.assertEqual(
                database.conn.execute(
                    "SELECT COUNT(*) FROM registry_entry_revisions"
                ).fetchone()[0],
                1,
            )
            self.assertEqual(
                database.conn.execute(
                    "SELECT COUNT(*) FROM workspace_item_revisions"
                ).fetchone()[0],
                1,
            )
            self.assertEqual(database.conn.execute("PRAGMA user_version").fetchone()[0], 6)
            # Jurisdiction package backfilled for the stub identity
            grant_count = database.conn.execute(
                "SELECT COUNT(*) FROM identity_grants WHERE object_identity_id = 'id-1'"
            ).fetchone()[0]
            self.assertEqual(grant_count, 5)
            # Profiles table present after migration 6
            self.assertEqual(
                database.conn.execute(
                    "SELECT COUNT(*) FROM access_jurisdiction_profiles"
                ).fetchone()[0],
                0,
            )

    def test_existing_database_is_not_overwritten(self):
        initialize_database(self.root, handle="me", preferred_name="Me")
        with self.assertRaisesRegex(RuntimeError, "already exists"):
            initialize_database(self.root, handle="new", preferred_name="New")

    def test_integrity_check_and_online_backup(self):
        initialize_database(self.root, handle="me", preferred_name="Me")
        check = database_integrity_check(self.root)
        self.assertTrue(check["ok"])
        self.assertEqual(check["integrity_check"], ["ok"])
        self.assertEqual(check["foreign_key_violations"], [])

        destination = Path(self._tmp.name) / "backup.sqlite3"
        result = backup_database(self.root, destination)
        self.assertEqual(result["destination"], str(destination.resolve()))
        self.assertGreater(result["bytes"], 0)
        with Database(destination) as database:
            self.assertEqual(
                database.conn.execute("SELECT local_handle FROM identity").fetchone()[0],
                "me",
            )

    def test_database_commands_emit_json(self):
        initialize_database(self.root, handle="me", preferred_name="Me")
        runner = CliRunner()

        info = runner.invoke(
            app, ["db", "info", "--path", str(self.root), "--json"]
        )
        self.assertEqual(info.exit_code, 0, info.output)
        self.assertEqual(json.loads(info.output)["schema_version"], 6)

        integrity = runner.invoke(
            app, ["db", "integrity-check", "--path", str(self.root), "--json"]
        )
        self.assertEqual(integrity.exit_code, 0, integrity.output)
        self.assertTrue(json.loads(integrity.output)["ok"])

        info_text = runner.invoke(
            app, ["db", "info", "--path", str(self.root), "--no-json"]
        )
        self.assertEqual(info_text.exit_code, 0, info_text.output)
        self.assertIn("schema_version: 6", info_text.output)
        self.assertFalse(info_text.output.lstrip().startswith("{"))

        integrity_text = runner.invoke(
            app,
            ["db", "integrity-check", "--path", str(self.root), "--no-json"],
        )
        self.assertEqual(integrity_text.exit_code, 0, integrity_text.output)
        self.assertIn("ok: True", integrity_text.output)


if __name__ == "__main__":
    unittest.main()
