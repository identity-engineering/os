"""Local Space + multi-Identity foundation tests (OS #77)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from typer.testing import CliRunner

from ie.cli import app
from runtime.context import get_active_identity, list_identities, list_spaces
from runtime.database import Database, SCHEMA_VERSION, initialize_database


class SpaceIdentityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "install"
        initialize_database(self.root, handle="me", preferred_name="Me")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_schema_at_least_v8_after_init(self) -> None:
        with Database(self.root) as database:
            version = int(database.conn.execute("PRAGMA user_version").fetchone()[0])
        self.assertGreaterEqual(version, 8)
        self.assertGreaterEqual(SCHEMA_VERSION, 8)

    def test_init_creates_local_space_and_membership(self) -> None:
        spaces = list_spaces(self.root)
        self.assertEqual(len(spaces), 1)
        self.assertEqual(spaces[0]["kind"], "local")
        active = get_active_identity(self.root)
        self.assertEqual(active["local_handle"], "me")

    def test_second_identity_and_switch(self) -> None:
        runner = CliRunner()
        created = runner.invoke(
            app,
            [
                "identity",
                "create",
                "--path",
                str(self.root),
                "--name",
                "Agent One",
                "--handle",
                "agent-one",
                "--substrate",
                "runtime",
            ],
        )
        self.assertEqual(created.exit_code, 0, created.output)
        body = json.loads(created.output)
        self.assertEqual(body["local_handle"], "agent-one")

        ids = list_identities(self.root)
        self.assertEqual(len(ids), 2)

        switched = runner.invoke(
            app, ["identity", "use", "agent-one", "--path", str(self.root)]
        )
        self.assertEqual(switched.exit_code, 0, switched.output)
        active = get_active_identity(self.root)
        self.assertEqual(active["local_handle"], "agent-one")


if __name__ == "__main__":
    unittest.main()
