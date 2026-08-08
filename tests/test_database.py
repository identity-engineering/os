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
                "SELECT local_handle, preferred_name FROM identity"
            ).fetchone()
            self.assertEqual(dict(identity), {"local_handle": "me", "preferred_name": "Me"})
            dimensions = connection.execute(
                "SELECT name FROM metric_dimensions ORDER BY name"
            ).fetchall()
            self.assertEqual([row[0] for row in dimensions], ["clarity_of_vision", "ownership_depth"])

        info = database_info(db_path)
        self.assertEqual(info["schema_version"], 1)
        self.assertEqual(info["foreign_keys"], 1)
        self.assertEqual(info["journal_mode"], "wal")
        self.assertGreaterEqual(info["table_count"], 20)

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
            self.assertEqual([tuple(row) for row in migrations], [(1, "initial_db_only_v1")])

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
        self.assertEqual(json.loads(info.output)["schema_version"], 1)

        integrity = runner.invoke(
            app, ["db", "integrity-check", "--path", str(self.root), "--json"]
        )
        self.assertEqual(integrity.exit_code, 0, integrity.output)
        self.assertTrue(json.loads(integrity.output)["ok"])


if __name__ == "__main__":
    unittest.main()