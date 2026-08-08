"""Focused tests for rebuilding SQLite projections from V1 history."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from typer.testing import CliRunner

from ie.cli import app
from runtime.apply import apply_interaction_signal
from runtime.database import Database, initialize_database
from runtime.mature import commit_mature
from runtime.models import InteractionSignal
from runtime.rebuild import rebuild_projections


class ProjectionRebuildTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.install = Path(self._tmp.name) / "install"
        initialize_database(self.install, handle="me", preferred_name="Me")
        self.source = self.install / "evidence.txt"
        self.source.write_text("rebuild evidence\n", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _query(self, sql: str, parameters=()):
        with Database(self.install) as database:
            return database.conn.execute(sql, parameters).fetchall()

    def test_rebuild_restores_projections_without_rewriting_history(self):
        signal = InteractionSignal(
            from_handle="alice",
            to_handle="me",
            timestamp="2026-08-08T12:00:00+00:00",
            interaction_depth_delta=0.4,
            sender_emergent_mass=61.0,
            sender_last_mature_at="2026-08-08T11:00:00+00:00",
        )
        apply_interaction_signal(signal, registry_root=self.install)
        mature = commit_mature(
            self.install,
            source_refs=["evidence.txt"],
            stem_differential={"state_delta_summary": "recovered"},
            workspace_changes=[
                {
                    "kind": "note",
                    "title": "Recovery note",
                    "content": "Projection can be reconstructed.",
                    "source_ref": "evidence.txt",
                }
            ],
            registry_changes=[
                {
                    "peer_handle": "alice",
                    "description": "trusted peer",
                    "my_mass_estimate": 72,
                    "mass_confidence": 0.8,
                    "dimensions": [
                        {"name": "clarity", "value": 0.7, "confidence": 0.9}
                    ],
                }
            ],
            capture_snapshots=True,
        )

        with Database(self.install) as database:
            with database.transaction():
                database.conn.execute(
                    "UPDATE foreign_estimates SET accumulated_depth = 0.0"
                )
                database.conn.execute("DELETE FROM registry_entries")
                database.conn.execute(
                    "UPDATE stem_state SET state_differential_json = '{}'"
                )
                database.conn.execute("DELETE FROM workspace_items")
                database.conn.execute(
                    "UPDATE identity SET last_signal_at = NULL, last_mature_at = NULL"
                )

        result = rebuild_projections(self.install)

        self.assertEqual(result["foreign_estimates"], 1)
        self.assertEqual(result["registry_entries"], 1)
        self.assertEqual(result["registry_dimensions"], 1)
        self.assertEqual(result["stem"], 1)
        self.assertEqual(result["workspace_items"], 1)
        foreign = self._query("SELECT * FROM foreign_estimates")[0]
        self.assertEqual(foreign["accumulated_depth"], 0.4)
        self.assertEqual(foreign["sender_emergent_mass"], 61.0)
        self.assertEqual(self._query("SELECT description FROM registry_entries")[0][0], "trusted peer")
        self.assertEqual(
            self._query("SELECT state_differential_json FROM stem_state")[0][0],
            '{"latest_summary":"recovered"}',
        )
        self.assertEqual(self._query("SELECT title FROM workspace_items")[0][0], "Recovery note")
        identity = self._query("SELECT last_signal_at, last_mature_at FROM identity")[0]
        self.assertEqual(identity["last_mature_at"], mature["last_mature_at"])
        self.assertIsNotNone(identity["last_signal_at"])
        self.assertEqual(len(self._query("SELECT * FROM interaction_events")), 1)
        self.assertEqual(len(self._query("SELECT * FROM apply_receipts")), 1)
        self.assertEqual(len(self._query("SELECT * FROM mature_events")), 1)
        self.assertEqual(len(self._query("SELECT * FROM registry_entry_revisions")), 2)
        self.assertEqual(len(self._query("SELECT * FROM stem_revisions")), 1)
        self.assertEqual(len(self._query("SELECT * FROM workspace_item_revisions")), 1)

    def test_rebuild_cli_requires_confirmation_and_emits_json(self):
        runner = CliRunner()
        blocked = runner.invoke(
            app,
            ["db", "rebuild-projections", "--path", str(self.install)],
        )
        self.assertNotEqual(blocked.exit_code, 0)
        self.assertIn("pass --yes", blocked.output)

        result = runner.invoke(
            app,
            [
                "db",
                "rebuild-projections",
                "--path",
                str(self.install),
                "--yes",
            ],
        )
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(json.loads(result.output)["foreign_estimates"], 0)


if __name__ == "__main__":
    unittest.main()
