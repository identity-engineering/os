"""Tests for the deterministic local identity-space export contract."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from runtime.apply import apply_from_dict
from runtime.database import initialize_database
from runtime.export import export_identity_space, verify_identity_export, write_identity_export
from runtime.jurisdiction import write_profile


class IdentityExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.install = Path(self._tmp.name) / "install"
        initialize_database(self.install, handle="me", preferred_name="Me")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_export_is_deterministic_and_preserves_contract_state(self):
        apply_from_dict(
            {
                "from": "alice",
                "to": "me",
                "timestamp": "2026-08-08T12:00:00+00:00",
                "existence": True,
                "interaction_depth_delta": 0.4,
                "sender_emergent_mass": 61.0,
            },
            registry_root=self.install,
            expected_to_handle="me",
        )
        write_profile(
            self.install,
            object_spec="self",
            access={"observe": 1.0},
            jurisdiction={"decide_goals": 1.0},
            confidence=0.8,
        )

        first = export_identity_space(self.install)
        second = export_identity_space(self.install)

        self.assertEqual(first, second)
        verified = verify_identity_export(first)
        tables = verified["payload"]["tables"]
        self.assertEqual(tables["identity"][0]["identity_id"], verified["payload"]["source"]["identity_id"])
        self.assertEqual(tables["foreign_estimates"][0]["sender_emergent_mass"], 61.0)
        self.assertNotIn("emergent_self_mass", json.dumps(first))
        self.assertEqual(len(tables["interaction_events"]), 1)
        self.assertEqual(len(tables["apply_receipts"]), 1)
        self.assertEqual(len(tables["identity_grants"]), 5)
        self.assertEqual(len(tables["spaces"]), 1)
        self.assertEqual(len(tables["space_memberships"]), 1)
        self.assertEqual(len(tables["access_jurisdiction_profiles"]), 1)

    def test_checksum_rejects_tampered_payload(self):
        document = export_identity_space(self.install)
        tampered = copy.deepcopy(document)
        tampered["payload"]["source"]["local_handle"] = "tampered"

        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            verify_identity_export(tampered)

    def test_write_export_outputs_json_and_summary(self):
        destination = self.install / "exports" / "identity.json"
        summary = write_identity_export(self.install, destination)

        self.assertTrue(destination.is_file())
        self.assertEqual(summary["export_id"], summary["payload_sha256"])
        parsed = json.loads(destination.read_text(encoding="utf-8"))
        self.assertEqual(parsed["payload_sha256"], summary["payload_sha256"])


if __name__ == "__main__":
    unittest.main()