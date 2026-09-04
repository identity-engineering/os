"""Tests for the local install status summary."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ie.status_cmd import collect_status, format_status
from runtime.database import Database, initialize_database
from runtime.mature import commit_mature


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

    def test_init_stem_is_present_and_unformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "install"
            initialize_database(root, handle="me", preferred_name="Me")

            status = collect_status(root)
            stem = status["stem"]

            self.assertTrue(status["has_stem"])
            self.assertTrue(stem["present"])
            self.assertFalse(stem["formed"])
            self.assertEqual(stem["revision"], 1)
            self.assertEqual(stem["revision_count"], 0)
            self.assertIsNone(stem["last_mature_id"])
            self.assertEqual(stem["state_differential"]["latest_summary"], "")
            self.assertEqual(stem["vision_gradient"]["latest_shift"], "")
            self.assertEqual(stem["coherence"]["latest_note"], "")
            self.assertNotIn("substance", stem)
            text = format_status(status)
            self.assertIn("x(t) present unformed", text)

    def test_mature_with_prose_marks_stem_formed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "install"
            initialize_database(root, handle="me", preferred_name="Me")
            source = root / "evidence.txt"
            source.write_text("causal evidence\n", encoding="utf-8")

            result = commit_mature(
                root,
                source_refs=["evidence.txt"],
                notes="integrated the causal chain",
                stem_differential={
                    "state_delta_summary": "moved from reaction to decision",
                    "vision_gradient_shift": "prioritize the next probe",
                    "coherence_note": "evidence and commitment now agree",
                },
            )

            status = collect_status(root)
            stem = status["stem"]

            self.assertTrue(stem["present"])
            self.assertTrue(stem["formed"])
            self.assertEqual(stem["revision"], 2)
            self.assertEqual(stem["revision_count"], 1)
            self.assertEqual(stem["last_mature_id"], result["mature_id"])
            self.assertEqual(
                stem["state_differential"]["latest_summary"],
                "moved from reaction to decision",
            )
            self.assertEqual(
                stem["vision_gradient"]["latest_shift"],
                "prioritize the next probe",
            )
            self.assertEqual(
                stem["coherence"]["latest_note"],
                "evidence and commitment now agree",
            )
            self.assertNotIn("substance", stem)
            text = format_status(status)
            self.assertIn("x(t) formed", text)
            self.assertIn("moved from reaction to decision", text)

    def test_substance_only_mature_stays_unformed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "install"
            initialize_database(root, handle="me", preferred_name="Me")
            source = root / "evidence.txt"
            source.write_text("causal evidence\n", encoding="utf-8")

            commit_mature(
                root,
                source_refs=["evidence.txt"],
                notes="substance bag only, no geometry slice",
                substance={"current_focus": "ownership probe"},
            )

            stem = collect_status(root)["stem"]
            self.assertTrue(stem["present"])
            self.assertFalse(stem["formed"])
            self.assertIsNotNone(stem["last_mature_id"])
            self.assertEqual(stem["revision_count"], 1)
            self.assertNotIn("substance", stem)


if __name__ == "__main__":
    unittest.main()
