"""Tests for identity grant list / revoke / residual protection."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from typer.testing import CliRunner

from ie.cli import app
from runtime.database import initialize_database
from runtime.grants import GrantError, list_grants, revoke_grant


class GrantCliTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "install"
        initialize_database(self.root, handle="me", preferred_name="Me")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_list_includes_creation_package(self) -> None:
        rows = list_grants(self.root)
        scopes = {r["scope"] for r in rows}
        self.assertIn("policy_admin", scopes)
        self.assertIn("grant_admin", scopes)
        self.assertIn("residual_emergency", scopes)
        residual = next(r for r in rows if r["scope"] == "residual_emergency")
        self.assertTrue(residual["residual"])
        self.assertFalse(residual["transferable"])

    def test_revoke_ordinary_scope(self) -> None:
        result = revoke_grant(self.root, scope="surface_admin", reason="test")
        self.assertEqual(result["status"], "revoked")
        active = list_grants(self.root)
        self.assertNotIn("surface_admin", {r["scope"] for r in active})

    def test_cannot_revoke_residual(self) -> None:
        with self.assertRaises(GrantError):
            revoke_grant(self.root, scope="residual_emergency")

    def test_cli_list_and_revoke(self) -> None:
        runner = CliRunner()
        listed = runner.invoke(app, ["grant", "list", "--path", str(self.root), "--json"])
        self.assertEqual(listed.exit_code, 0, listed.output)
        payload = json.loads(listed.output)
        self.assertGreaterEqual(len(payload["grants"]), 5)

        revoked = runner.invoke(
            app,
            [
                "grant",
                "revoke",
                "--path",
                str(self.root),
                "--scope",
                "visibility_control",
                "--reason",
                "cli-test",
            ],
        )
        self.assertEqual(revoked.exit_code, 0, revoked.output)
        body = json.loads(revoked.output)
        self.assertEqual(body["status"], "revoked")


if __name__ == "__main__":
    unittest.main()
