"""Tests for persistent consent and quarantine policy mutations."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from typer.testing import CliRunner

from ie.cli import app
from runtime.apply import apply_from_dict
from runtime.database import initialize_database
from runtime.models import ApplyStatus
from runtime.policy_store import (
    grant_consent,
    policy_snapshot,
    quarantine_sender,
    release_quarantine,
    revoke_consent,
)
from runtime.sqlite_store import SQLiteStore


class PolicyStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.install = Path(self._tmp.name) / "install"
        initialize_database(self.install, handle="me", preferred_name="Me")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _payload(self, **overrides):
        payload = {
            "from": "alice",
            "to": "me",
            "timestamp": "2026-08-08T12:00:00+00:00",
            "existence": True,
            "interaction_depth_delta": 0.2,
        }
        payload.update(overrides)
        return payload

    def test_policy_mutations_persist_and_apply_after_reload(self):
        grant_consent(
            self.install,
            sender_handle="alice",
            field_name="coarse_mass_estimate",
            reason="calibration session",
        )
        policy = SQLiteStore(self.install).load_policy()
        self.assertIn("coarse_mass_estimate", policy.grants["alice"])

        receipt = apply_from_dict(
            self._payload(coarse_mass_estimate=64, mass_confidence=0.8),
            registry_root=self.install,
            expected_to_handle="me",
        )
        self.assertEqual(receipt.status, ApplyStatus.PARTIAL)
        self.assertIn("coarse_mass_estimate", receipt.applied_fields)

        revoke_consent(
            self.install,
            sender_handle="alice",
            field_name="coarse_mass_estimate",
            reason="pause calibration",
        )
        quarantine_sender(
            self.install,
            sender_handle="alice",
            reason="boundary test",
        )
        quarantined = SQLiteStore(self.install).load_policy()
        self.assertIn("alice", quarantined.quarantined_handles)
        quarantined_receipt = apply_from_dict(
            self._payload(coarse_mass_estimate=70),
            registry_root=self.install,
            expected_to_handle="me",
        )
        self.assertTrue(quarantined_receipt.quarantine)
        self.assertNotIn("coarse_mass_estimate", quarantined_receipt.applied_fields)

        release_quarantine(
            self.install,
            sender_handle="alice",
            reason="boundary test complete",
        )
        snapshot = policy_snapshot(self.install)
        self.assertEqual(snapshot["grants"], [])
        self.assertEqual(snapshot["quarantines"], [])
        self.assertEqual(snapshot["policy_event_count"], 4)

    def test_policy_commands_mutate_sqlite_and_emit_json(self):
        runner = CliRunner()
        grant = runner.invoke(
            app,
            [
                "policy",
                "grant",
                "--path",
                str(self.install),
                "--from",
                "alice",
                "--field",
                "mass_confidence",
            ],
        )
        self.assertEqual(grant.exit_code, 0, grant.output)
        self.assertTrue(json.loads(grant.output)["changed"])

        show = runner.invoke(
            app, ["policy", "show", "--path", str(self.install)]
        )
        self.assertEqual(show.exit_code, 0, show.output)
        shown = json.loads(show.output)
        self.assertEqual(shown["grants"][0]["field_name"], "mass_confidence")

        registry = runner.invoke(
            app, ["registry", "list", "--path", str(self.install), "--json"]
        )
        self.assertEqual(registry.exit_code, 0, registry.output)
        self.assertEqual(json.loads(registry.output)["peers"], [])

        requests = runner.invoke(
            app, ["request", "list", "--path", str(self.install), "--json"]
        )
        self.assertEqual(requests.exit_code, 0, requests.output)
        self.assertEqual(json.loads(requests.output)["requests"], [])

        quarantine = runner.invoke(
            app,
            [
                "policy",
                "quarantine",
                "--path",
                str(self.install),
                "--from",
                "alice",
                "--reason",
                "manual boundary",
            ],
        )
        self.assertEqual(quarantine.exit_code, 0, quarantine.output)
        self.assertTrue(json.loads(quarantine.output)["active"])


if __name__ == "__main__":
    unittest.main()