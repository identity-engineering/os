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
    evaluate_space_access,
    export_space_boundary,
    list_spaces,
    verify_space_boundary,
)


class SpaceBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "install"
        metadata = initialize_database(self.root, handle="me", preferred_name="Me")
        self.space_id = metadata["identity_id"]

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
        remote_root = self.root.parent / "remote"
        remote_metadata = initialize_database(remote_root, handle="remote", preferred_name="Remote")
        boundary = export_space_boundary(remote_root, space_id=remote_metadata["identity_id"])
        result = accept_inbound_boundary(
            boundary,
            expected_space_id=remote_metadata["identity_id"],
            install_root=self.root,
        )
        self.assertEqual(result["status"], "known")
        self.assertFalse(result["addressable"])
        self.assertFalse(result["private_geometry_accepted"])
        self.assertTrue(result["registered"])
        spaces = list_spaces(self.root)
        remote = next(space for space in spaces if space["space_id"] == remote_metadata["identity_id"])
        self.assertFalse(remote["addressable"])
        decision = evaluate_space_access(
            self.root,
            space_id=remote_metadata["identity_id"],
            capability="surface",
        )
        self.assertFalse(decision["allowed"])
        self.assertEqual(decision["reason"], "active_membership_required")

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