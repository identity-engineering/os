"""Tests for the public Space boundary and inbound membrane contract."""

from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from runtime.database import initialize_database
from runtime.membrane import (
    MembraneError,
    accept_inbound_boundary,
    export_space_boundary,
    verify_space_boundary,
)


class SpaceBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "install"
        initialize_database(self.root, handle="me", preferred_name="Me")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_boundary_contains_public_descriptor_only(self) -> None:
        boundary = export_space_boundary(self.root)
        payload = boundary["payload"]
        self.assertEqual(payload["membrane"]["addressable"], False)
        self.assertFalse(payload["membrane"]["export_policy"]["full_private_geometry"])
        self.assertNotIn("tables", payload)
        self.assertNotIn("identity_grants", payload)
        self.assertEqual(verify_space_boundary(boundary), boundary)

    def test_inbound_boundary_is_known_but_not_addressable(self) -> None:
        boundary = export_space_boundary(self.root, space_id="space-a")
        result = accept_inbound_boundary(boundary, expected_space_id="space-a")
        self.assertEqual(result["status"], "known")
        self.assertFalse(result["addressable"])
        self.assertFalse(result["private_geometry_accepted"])

    def test_boundary_rejects_tampering_and_private_payload(self) -> None:
        boundary = export_space_boundary(self.root)
        tampered = copy.deepcopy(boundary)
        tampered["payload"]["tables"] = {"identity": []}
        with self.assertRaisesRegex(MembraneError, "envelope|payload|checksum"):
            verify_space_boundary(tampered)

        private = copy.deepcopy(boundary)
        private["payload"]["membrane"]["export_policy"]["full_private_geometry"] = True
        with self.assertRaisesRegex(MembraneError, "checksum|export policy"):
            verify_space_boundary(private)


if __name__ == "__main__":
    unittest.main()