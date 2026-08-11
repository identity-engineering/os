"""Access & Jurisdiction probe write path (issue #40)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from typer.testing import CliRunner

from ie.cli import app
from runtime.database import Database, initialize_database, utcnow
from runtime.jurisdiction import (
    JurisdictionError,
    get_profile,
    list_grants,
    list_profiles,
    revoke_grant,
    transfer_grant,
    write_profile,
)


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


class JurisdictionGrantTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "install"
        metadata = initialize_database(self.root, handle="me", preferred_name="Me")
        self.identity_id = metadata["identity_id"]
        self.other_identity_id = str(uuid4())
        with Database(self.root) as database:
            now = utcnow()
            install_id = str(uuid4())
            database.conn.execute(
                "INSERT INTO install(install_id, created_at, updated_at) VALUES (?, ?, ?)",
                (install_id, now, now),
            )
            database.conn.execute(
                """
                INSERT INTO identity(
                    identity_id, install_id, local_handle, preferred_name, substrate,
                    accepts_ie_signals, created_at, updated_at, creator_identity_id
                ) VALUES (?, ?, ?, ?, 'human', 1, ?, ?, ?)
                """,
                (
                    self.other_identity_id,
                    install_id,
                    "other",
                    "Other",
                    now,
                    now,
                    self.identity_id,
                ),
            )
            database.conn.commit()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_transfer_revokes_source_and_creates_target_grant(self) -> None:
        grants = list_grants(self.root)
        source = next(grant for grant in grants if grant["scope"] == "policy_admin")

        result = transfer_grant(
            self.root,
            grant_id=source["grant_id"],
            to_identity_id=self.other_identity_id,
            note="delegate policy work",
        )

        self.assertEqual(result["status"], "transferred")
        self.assertEqual(result["actor_identity_id"], self.identity_id)
        active = list_grants(self.root)
        self.assertEqual(len(active), 5)
        self.assertIn(self.other_identity_id, {grant["actor_identity_id"] for grant in active})
        historical = list_grants(self.root, include_revoked=True)
        original = next(grant for grant in historical if grant["grant_id"] == source["grant_id"])
        self.assertEqual(original["revoked_by_identity_id"], self.identity_id)
        self.assertEqual(original["revocation_note"], "delegate policy work")

    def test_object_identity_can_revoke_ordinary_grant_but_not_residual(self) -> None:
        grants = list_grants(self.root)
        ordinary = next(grant for grant in grants if grant["scope"] == "surface_admin")
        result = revoke_grant(self.root, grant_id=ordinary["grant_id"], note="child boundary")
        self.assertEqual(result["status"], "revoked")

        residual = next(grant for grant in grants if grant["scope"] == "residual_emergency")
        with self.assertRaisesRegex(JurisdictionError, "residual"):
            revoke_grant(self.root, grant_id=residual["grant_id"])

    def test_residual_grant_cannot_transfer(self) -> None:
        residual = next(
            grant for grant in list_grants(self.root) if grant["scope"] == "residual_emergency"
        )
        with self.assertRaisesRegex(JurisdictionError, "residual"):
            transfer_grant(
                self.root,
                grant_id=residual["grant_id"],
                to_identity_id=self.other_identity_id,
            )

    def test_space_scoped_grant_admin_can_revoke_ordinary_grant(self) -> None:
        target_grant_id = str(uuid4())
        admin_grant_id = str(uuid4())
        now = utcnow()
        with Database(self.root) as database:
            database.conn.execute(
                """
                INSERT INTO identity_grants(
                    grant_id, actor_identity_id, object_identity_id, scope, residual,
                    transferable, space_id, granted_at, revoked_at,
                    granted_by_identity_id, note
                ) VALUES (?, ?, ?, 'surface_admin', 0, 1, 'space-a', ?, NULL, ?, '')
                """,
                (
                    target_grant_id,
                    self.other_identity_id,
                    self.other_identity_id,
                    now,
                    self.identity_id,
                ),
            )
            database.conn.execute(
                """
                INSERT INTO identity_grants(
                    grant_id, actor_identity_id, object_identity_id, scope, residual,
                    transferable, space_id, granted_at, revoked_at,
                    granted_by_identity_id, note
                ) VALUES (?, ?, ?, 'grant_admin', 0, 1, 'space-a', ?, NULL, ?, '')
                """,
                (
                    admin_grant_id,
                    self.identity_id,
                    self.other_identity_id,
                    now,
                    self.identity_id,
                ),
            )
            database.conn.commit()

        result = revoke_grant(self.root, grant_id=target_grant_id, note="space admin")
        self.assertEqual(result["status"], "revoked")

    def test_cli_grant_lifecycle_and_boundary_commands(self) -> None:
        runner = CliRunner()
        listed = runner.invoke(
            app,
            [
                "jurisdiction",
                "grant",
                "list",
                "--path",
                str(self.root),
                "--json",
            ],
        )
        self.assertEqual(listed.exit_code, 0, listed.output)
        grants = json.loads(listed.output)["grants"]
        source = next(grant for grant in grants if grant["scope"] == "policy_admin")

        transferred = runner.invoke(
            app,
            [
                "jurisdiction",
                "grant",
                "transfer",
                "--path",
                str(self.root),
                "--grant",
                source["grant_id"],
                "--to",
                self.other_identity_id,
                "--note",
                "cli delegation",
            ],
        )
        self.assertEqual(transferred.exit_code, 0, transferred.output)
        self.assertEqual(json.loads(transferred.output)["status"], "transferred")

        ordinary = next(grant for grant in grants if grant["scope"] == "surface_admin")
        revoked = runner.invoke(
            app,
            [
                "jurisdiction",
                "grant",
                "revoke",
                "--path",
                str(self.root),
                "--grant",
                ordinary["grant_id"],
            ],
        )
        self.assertEqual(revoked.exit_code, 0, revoked.output)
        self.assertEqual(json.loads(revoked.output)["status"], "revoked")

        boundary_path = self.root / "boundary.json"
        exported = runner.invoke(
            app,
            [
                "space",
                "boundary",
                "export",
                "--path",
                str(self.root),
                "--to",
                str(boundary_path),
                "--space-id",
                "space-cli",
            ],
        )
        self.assertEqual(exported.exit_code, 0, exported.output)
        self.assertTrue(boundary_path.is_file())

        verified = runner.invoke(
            app,
            [
                "space",
                "boundary",
                "verify",
                "--from",
                str(boundary_path),
                "--space-id",
                "space-cli",
            ],
        )
        self.assertEqual(verified.exit_code, 0, verified.output)
        verification = json.loads(verified.output)
        self.assertTrue(verification["verified"])
        self.assertEqual(verification["status"], "known")
        self.assertFalse(verification["addressable"])


if __name__ == "__main__":
    unittest.main()
