"""Tests for Effective Freedom derived readout."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from typer.testing import CliRunner

from ie.cli import app
from runtime.apply import apply_interaction_signal
from runtime.database import Database, initialize_database
from runtime.freedom import BASELINE_UNBOUND, compute_freedom_readout
from runtime.models import InteractionSignal


class FreedomReadoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "install"
        initialize_database(self.root, handle="me", preferred_name="Me")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_baseline_without_receipts(self) -> None:
        readout = compute_freedom_readout(self.root)
        self.assertEqual(readout.formula_version, "0")
        self.assertGreaterEqual(readout.effective_freedom, 0.0)
        self.assertEqual(readout.unbound_dof, BASELINE_UNBOUND)
        self.assertGreaterEqual(readout.constraint_intensity, 0.0)
        self.assertIn("cold baseline", " ".join(readout.notes))

    def test_receipt_unbound_raises_freedom(self) -> None:
        with Database(self.root) as database:
            install_id = database.conn.execute(
                "SELECT install_id FROM install LIMIT 1"
            ).fetchone()[0]
            database.conn.execute(
                """
                INSERT INTO geometry_receipts(
                    receipt_id, install_id, timestamp, mode, observer, target,
                    degrees_of_freedom_json, tension_components_json, notes
                ) VALUES (?, ?, ?, 'interact', 'me', 'alice', ?, '[]', '')
                """,
                (
                    "receipt-high-dof",
                    install_id,
                    "2026-08-13T12:00:00+00:00",
                    json.dumps(
                        {
                            "unbound_estimate": 4.0,
                            "constraints_noted": [],
                            "confidence": 0.8,
                        }
                    ),
                ),
            )
            database.conn.commit()

        readout = compute_freedom_readout(self.root)
        self.assertGreaterEqual(readout.unbound_dof, 4.0)
        self.assertGreater(readout.effective_freedom, BASELINE_UNBOUND)

    def test_constraints_and_quarantine_increase_intensity(self) -> None:
        with Database(self.root) as database:
            identity_id = database.conn.execute(
                "SELECT identity_id FROM identity LIMIT 1"
            ).fetchone()[0]
            install_id = database.conn.execute(
                "SELECT install_id FROM install LIMIT 1"
            ).fetchone()[0]
            database.conn.execute(
                """
                INSERT INTO geometry_receipts(
                    receipt_id, install_id, timestamp, mode, observer, target,
                    degrees_of_freedom_json, tension_components_json, notes
                ) VALUES (?, ?, ?, 'interact', 'me', 'alice', ?, '[]', '')
                """,
                (
                    "receipt-constrained",
                    install_id,
                    "2026-08-13T12:00:00+00:00",
                    json.dumps(
                        {
                            "unbound_estimate": 2.0,
                            "constraints_noted": ["membrane", "reputation", "habit"],
                        }
                    ),
                ),
            )
            database.conn.execute(
                """
                INSERT INTO quarantines(
                    quarantine_id, identity_id, sender_handle, active, reason,
                    created_at, source
                ) VALUES ('q1', ?, 'spam', 1, 'test', '2026-08-13T12:00:00+00:00', 'test')
                """,
                (identity_id,),
            )
            database.conn.commit()

        readout = compute_freedom_readout(self.root)
        self.assertGreater(readout.constraint_intensity, 0.0)
        # With constraints, freedom should be below unbound
        self.assertLess(readout.effective_freedom, readout.unbound_dof)

    def test_feed_tension_enters_intensity(self) -> None:
        signal = InteractionSignal(
            from_handle="alice",
            to_handle="me",
            timestamp="2026-08-13T12:00:00+00:00",
            interaction_depth_delta=0.4,
            sender_emergent_mass=55.0,
        )
        apply_interaction_signal(signal, registry_root=self.root)
        readout = compute_freedom_readout(self.root)
        # After interact+feed, registry may carry effect_on_me tension
        self.assertIn("mean_abs_tension_sum", readout.sources)
        self.assertGreaterEqual(readout.effective_freedom, 0.0)

    def test_cli_freedom_json(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            app, ["freedom", "--path", str(self.root), "--json"]
        )
        self.assertEqual(result.exit_code, 0, result.output)
        payload = json.loads(result.output)
        self.assertIn("effective_freedom", payload)
        self.assertIn("unbound_dof", payload)
        self.assertIn("constraint_intensity", payload)
        self.assertEqual(payload["formula_version"], "0")


if __name__ == "__main__":
    unittest.main()
