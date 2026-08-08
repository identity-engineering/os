"""Focused tests for the SQLite Mature transaction."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from runtime.database import Database, initialize_database
from runtime.mature import MatureError, commit_mature
from runtime.mass import build_public_card


class MatureTransactionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.install = Path(self._tmp.name) / "install"
        initialize_database(self.install, handle="me", preferred_name="Me")
        self.source = self.install / "evidence.txt"
        self.source.write_text("causal evidence\n", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _query(self, sql: str, parameters=()):
        with Database(self.install) as database:
            return database.conn.execute(sql, parameters).fetchall()

    def test_commit_updates_owned_state_and_audit_atomically(self):
        result = commit_mature(
            self.install,
            source_refs=["evidence.txt"],
            notes="integrated the causal chain",
            stem_differential={
                "state_delta_summary": "moved from reaction to decision",
                "vision_gradient_shift": "prioritize the next probe",
                "coherence_note": "evidence and commitment now agree",
            },
            substance={"current_focus": "ownership probe"},
            workspace_changes=[
                {
                    "kind": "commitment",
                    "title": "Run ownership probe",
                    "content": "Prepare the next concrete test.",
                    "source_ref": "evidence.txt",
                }
            ],
            registry_changes=[
                {
                    "peer_handle": "alice",
                    "my_mass_estimate": 72,
                    "mass_confidence": 0.8,
                    "peer_last_mature_at": "2026-08-08T10:00:00+00:00",
                    "dimensions": [
                        {
                            "name": "clarity",
                            "value": 0.7,
                            "confidence": 0.9,
                        }
                    ],
                }
            ],
            reassessment_targets=["alice"],
            capture_snapshots=True,
        )

        self.assertTrue(result["mature_id"])
        self.assertEqual(result["registry_change_count"], 1)
        self.assertEqual(result["workspace_change_count"], 1)
        self.assertEqual(len(result["reassessment_request_ids"]), 1)

        mature_rows = self._query("SELECT * FROM mature_events")
        self.assertEqual(len(mature_rows), 1)
        self.assertEqual(mature_rows[0]["mature_id"], result["mature_id"])
        self.assertEqual(mature_rows[0]["source_count"], 1)
        self.assertEqual(len(self._query("SELECT * FROM evidence_sources")), 1)
        self.assertEqual(len(self._query("SELECT * FROM stem_revisions")), 1)
        self.assertEqual(len(self._query("SELECT * FROM workspace_items")), 1)
        self.assertEqual(len(self._query("SELECT * FROM workspace_item_revisions")), 1)
        self.assertEqual(len(self._query("SELECT * FROM registry_entries")), 1)
        self.assertEqual(len(self._query("SELECT * FROM registry_entry_revisions")), 1)
        self.assertEqual(len(self._query("SELECT * FROM registry_dimension_values")), 1)
        self.assertEqual(len(self._query("SELECT * FROM trajectory_entries")), 1)
        self.assertEqual(len(self._query("SELECT * FROM geometry_receipts")), 1)

        request = self._query("SELECT * FROM estimate_requests")[0]
        self.assertEqual(request["direction"], "outbound")
        self.assertEqual(request["mature_id"], result["mature_id"])

        identity = self._query("SELECT * FROM identity")[0]
        self.assertEqual(identity["last_mature_at"], result["last_mature_at"])
        stem = self._query("SELECT * FROM stem_state")[0]
        substance = json.loads(stem["substance_json"])
        self.assertNotIn("owned_mass", substance)
        self.assertEqual(substance["current_focus"], "ownership probe")
        card = build_public_card(local_handle="me", registry_root=self.install)
        self.assertEqual(card["last_mature_at"], result["last_mature_at"])

    def test_invalid_change_rolls_back_all_writes(self):
        with self.assertRaises(MatureError):
            commit_mature(
                self.install,
                source_refs=["evidence.txt"],
                notes="should not commit",
                registry_changes=[
                    {
                        "peer_handle": "alice",
                        "my_mass_estimate": 50,
                        "mass_confidence": 0.5,
                    }
                ],
                workspace_changes=[
                    {
                        "operation": "update",
                        "item_id": "missing-item",
                        "content": "invalid",
                    }
                ],
            )

        self.assertEqual(len(self._query("SELECT * FROM mature_events")), 0)
        self.assertEqual(len(self._query("SELECT * FROM evidence_sources")), 0)
        self.assertEqual(len(self._query("SELECT * FROM registry_entries")), 0)
        self.assertEqual(len(self._query("SELECT * FROM workspace_items")), 0)
        self.assertIsNone(self._query("SELECT last_mature_at FROM identity")[0][0])

    def test_invalid_substance_and_registry_depth_are_rejected(self):
        with self.assertRaisesRegex(MatureError, "substance must be an object"):
            commit_mature(
                self.install,
                source_refs=["evidence.txt"],
                substance=["not", "an", "object"],
            )

        with self.assertRaisesRegex(MatureError, "interaction_depth"):
            commit_mature(
                self.install,
                source_refs=["evidence.txt"],
                registry_changes=[
                    {
                        "peer_handle": "alice",
                        "interaction_depth": 1.1,
                    }
                ],
            )


if __name__ == "__main__":
    unittest.main()