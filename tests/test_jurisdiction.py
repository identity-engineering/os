"""Access & Jurisdiction probe write path (issue #40)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from runtime.database import initialize_database
from runtime.jurisdiction import get_profile, list_profiles, write_profile


class JurisdictionProbeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "install"
        initialize_database(self.root, handle="me", preferred_name="Me")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_write_and_read_self_profile(self):
        result = write_profile(
            self.root,
            object_spec="self",
            access={"reach": 1.0, "use": 1.0, "observe": 1.0, "affected_by": 1.0},
            jurisdiction={
                "decide_goals": 1.0,
                "constrain": 1.0,
                "transfer": 1.0,
                "destroy": 1.0,
                "redefine_boundary": 1.0,
            },
            confidence=0.9,
            notes="sovereignty self-check",
            source="test",
        )
        self.assertEqual(result["object_kind"], "self")
        self.assertEqual(result["revision"], 1)
        self.assertAlmostEqual(result["confidence"], 0.9)

        loaded = get_profile(self.root, object_spec="self")
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded["profile_id"], result["profile_id"])
        self.assertEqual(loaded["access"]["reach"], 1.0)

        rows = list_profiles(self.root)
        self.assertEqual(len(rows), 1)

    def test_revision_increments(self):
        write_profile(
            self.root,
            object_spec="peer:alice",
            access={"reach": 0.5},
            jurisdiction={"constrain": 0.2},
            confidence=0.4,
        )
        second = write_profile(
            self.root,
            object_spec="peer:alice",
            access={"reach": 0.7},
            jurisdiction={"constrain": 0.3},
            confidence=0.6,
        )
        self.assertEqual(second["revision"], 2)
        latest = get_profile(self.root, object_spec="peer:alice")
        assert latest is not None
        self.assertEqual(latest["revision"], 2)
        self.assertAlmostEqual(latest["access"]["reach"], 0.7)


if __name__ == "__main__":
    unittest.main()
