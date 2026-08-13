"""Tests for Space membrane policy (OS #82)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from runtime.apply import apply_from_dict
from runtime.database import Database, canonical_json, initialize_database
from runtime.export import export_identity_space
from runtime.membrane import (
    default_local_membrane_policy,
    filter_export_tables,
    filter_inbound_fields,
    parse_membrane_policy,
)
from runtime.policy import LocalPolicy


class MembraneUnitTests(unittest.TestCase):
    def test_default_local_policy_shape(self):
        pol = default_local_membrane_policy()
        self.assertEqual(pol["version"], 1)
        self.assertEqual(pol["export"]["mode"], "owner_full")
        self.assertEqual(pol["inbound"]["mode"], "surface_default")

    def test_parse_empty_falls_back_to_default(self):
        self.assertEqual(parse_membrane_policy("{}"), default_local_membrane_policy())
        self.assertEqual(parse_membrane_policy(None), default_local_membrane_policy())

    def test_export_allowlist_strips_tables(self):
        policy = {
            "version": 1,
            "export": {
                "mode": "allowlist",
                "allow_tables": ["identity_core", "metric"],
                "deny_tables": [],
            },
            "inbound": {"mode": "surface_default", "allow_fields": None, "deny_fields": []},
        }
        result = filter_export_tables(
            ["identity", "metric_dimensions", "foreign_estimates", "registry_entries"],
            policy,
        )
        self.assertIn("identity", result.allowed_tables)
        self.assertIn("metric_dimensions", result.allowed_tables)
        self.assertIn("foreign_estimates", result.stripped_tables)
        self.assertIn("registry_entries", result.stripped_tables)

    def test_inbound_deny_fields(self):
        policy = {
            "version": 1,
            "export": {"mode": "owner_full", "allow_tables": None, "deny_tables": []},
            "inbound": {
                "mode": "surface_default",
                "allow_fields": None,
                "deny_fields": ["relation_pull", "dimensions_delta"],
            },
        }
        result = filter_inbound_fields(
            ["existence", "interaction_depth_delta", "relation_pull", "dimensions_delta"],
            policy,
        )
        self.assertEqual(
            list(result.allowed_fields),
            ["existence", "interaction_depth_delta"],
        )
        self.assertEqual(set(result.stripped_fields), {"relation_pull", "dimensions_delta"})


class MembraneIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.install = Path(self._tmp.name) / "install"
        initialize_database(self.install, handle="me", preferred_name="Me")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_new_space_gets_default_membrane_policy(self):
        with Database(self.install) as database:
            row = database.conn.execute("SELECT policy_json FROM spaces LIMIT 1").fetchone()
        self.assertIsNotNone(row)
        parsed = json.loads(row["policy_json"])
        self.assertEqual(parsed["export"]["mode"], "owner_full")

    def test_export_default_includes_interaction_tables(self):
        apply_from_dict(
            {
                "from": "alice",
                "to": "me",
                "timestamp": "2026-08-13T12:00:00+00:00",
                "existence": True,
                "interaction_depth_delta": 0.2,
                "sender_emergent_mass": 10.0,
            },
            registry_root=self.install,
            expected_to_handle="me",
        )
        document = export_identity_space(self.install)
        tables = document["payload"]["tables"]
        self.assertIn("foreign_estimates", tables)
        self.assertEqual(document["payload"]["membrane"]["stripped_tables"], [])

    def test_export_respects_allowlist_policy(self):
        with Database(self.install) as database:
            with database.transaction() as conn:
                policy = {
                    "version": 1,
                    "export": {
                        "mode": "allowlist",
                        "allow_tables": ["identity_core"],
                        "deny_tables": [],
                    },
                    "inbound": {
                        "mode": "surface_default",
                        "allow_fields": None,
                        "deny_fields": [],
                    },
                }
                conn.execute(
                    "UPDATE spaces SET policy_json = ?",
                    (canonical_json(policy),),
                )

        document = export_identity_space(self.install)
        tables = document["payload"]["tables"]
        self.assertIn("identity", tables)
        self.assertNotIn("foreign_estimates", tables)
        self.assertIn("foreign_estimates", document["payload"]["membrane"]["stripped_tables"])

    def test_inbound_membrane_strips_denied_fields(self):
        with Database(self.install) as database:
            with database.transaction() as conn:
                policy = {
                    "version": 1,
                    "export": {
                        "mode": "owner_full",
                        "allow_tables": None,
                        "deny_tables": [],
                    },
                    "inbound": {
                        "mode": "surface_default",
                        "allow_fields": None,
                        "deny_fields": ["sender_emergent_mass"],
                    },
                }
                conn.execute(
                    "UPDATE spaces SET policy_json = ?",
                    (canonical_json(policy),),
                )

        receipt = apply_from_dict(
            {
                "from": "bob",
                "to": "me",
                "timestamp": "2026-08-13T13:00:00+00:00",
                "existence": True,
                "interaction_depth_delta": 0.3,
                "sender_emergent_mass": 42.0,
            },
            registry_root=self.install,
            expected_to_handle="me",
            policy=LocalPolicy(open_consent=True),
        )
        self.assertNotIn("sender_emergent_mass", receipt.applied_fields)
        self.assertIn("membrane_stripped=sender_emergent_mass", receipt.reason or "")


if __name__ == "__main__":
    unittest.main()
