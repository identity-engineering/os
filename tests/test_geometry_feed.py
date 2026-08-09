"""Geometry Receipt feed write-back (OS #8)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from runtime.apply import apply_from_dict
from runtime.database import Database, database_path, initialize_database
from runtime.geometry_feed import feed_pending, feed_receipt


class GeometryFeedTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "install"
        initialize_database(self.root, handle="me", preferred_name="Me")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_apply_hook_feeds_registry_effect_on_me(self) -> None:
        receipt = apply_from_dict(
            {
                "from": "alice",
                "to": "me",
                "existence": True,
                "interaction_depth_delta": 0.2,
                "sender_emergent_mass": 55.0,
            },
            registry_root=self.root,
            expected_to_handle="me",
        )
        self.assertIn(receipt.status.value, {"applied", "partial"})
        self.assertIn("geometry_receipt=", receipt.reason or "")
        self.assertIn("geometry_fed=", receipt.reason or "")

        with Database(database_path(self.root)) as database:
            entry = database.conn.execute(
                "SELECT effect_on_me_json, revision, source FROM registry_entries WHERE peer_handle = ?",
                ("alice",),
            ).fetchone()
            self.assertIsNotNone(entry)
            effect = json.loads(entry["effect_on_me_json"])
            self.assertEqual(effect["source_mode"], "interact")
            self.assertIsNotNone(effect.get("last_geometry_receipt_id"))
            self.assertIn("tension_components", effect)
            self.assertEqual(entry["source"], "geometry_feed")

            geo = database.conn.execute(
                "SELECT fed_at FROM geometry_receipts WHERE receipt_id = ?",
                (effect["last_geometry_receipt_id"],),
            ).fetchone()
            self.assertIsNotNone(geo["fed_at"])

    def test_explicit_feed_is_idempotent(self) -> None:
        apply_from_dict(
            {
                "from": "bob",
                "to": "me",
                "existence": True,
                "interaction_depth_delta": 0.1,
            },
            registry_root=self.root,
            expected_to_handle="me",
        )
        first = feed_pending(self.root, limit=10)
        # Already fed by hook; pending batch should be empty or already_fed
        self.assertEqual(first["errors"], 0)

        with Database(database_path(self.root)) as database:
            row = database.conn.execute(
                "SELECT receipt_id FROM geometry_receipts ORDER BY timestamp DESC LIMIT 1"
            ).fetchone()
            rid = row["receipt_id"]

        second = feed_receipt(self.root, rid)
        self.assertEqual(second["status"], "already_fed")


if __name__ == "__main__":
    unittest.main()
