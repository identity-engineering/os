"""Tests for the local install status summary."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from runtime.database import Database, initialize_database
from ie.status_cmd import collect_status


class StatusTests(unittest.TestCase):
    def test_status_reads_foreign_estimates_from_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "install"
            initialize_database(root, handle="me", preferred_name="Me")
            with Database(root) as database:
                identity_id = database.conn.execute(
                    "SELECT identity_id FROM identity"
                ).fetchone()[0]
                with database.transaction():
                    database.conn.execute(
                        """
                        INSERT INTO foreign_estimates(
                            identity_id, sender_handle, first_signal_at, last_signal_at
                        ) VALUES (?, 'alice', '2026-08-08T00:00:00+00:00', '2026-08-08T00:00:00+00:00')
                        """,
                        (identity_id,),
                    )

            status = collect_status(root)

            self.assertEqual(status["foreign_estimate_senders"], ["alice"])
            self.assertEqual(status["handle"], "me")


if __name__ == "__main__":
    unittest.main()