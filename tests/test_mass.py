"""Unit tests for emergent self-Mass aggregation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from runtime.mass import (
    M_UNKNOWN,
    build_public_card,
    compute_mass_readout,
    depth_factor,
    weight_for,
)
from runtime.database import initialize_database
from runtime.models import ForeignEstimateRecord
from runtime.sqlite_store import SQLiteStore


class MassFormulaTests(unittest.TestCase):
    def test_depth_factor_bounds(self):
        self.assertEqual(depth_factor(0.0), 0.0)
        self.assertAlmostEqual(depth_factor(1.0), 0.5)
        self.assertLess(depth_factor(10.0), 1.0)
        self.assertGreater(depth_factor(10.0), depth_factor(1.0))

    def test_weight_scales_with_sender_mass(self):
        low = weight_for(sender_mass=10, confidence=1.0, accumulated_depth=1.0)
        high = weight_for(sender_mass=80, confidence=1.0, accumulated_depth=1.0)
        self.assertGreater(high, low)


class MassReadoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.install = Path(self._tmp.name) / "install"
        initialize_database(self.install, handle="me", preferred_name="Me")
        self.registry = self.install
        self.store = SQLiteStore(self.install)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _save_estimate(
        self,
        handle: str,
        *,
        estimate: float | None,
        confidence: float | None = 0.8,
        depth: float = 1.0,
        quarantine: bool = False,
        existence: bool = True,
        sender_emergent_mass: float | None = None,
    ) -> None:
        rec = ForeignEstimateRecord(
            sender_handle=handle,
            first_signal_at="2026-07-31T00:00:00+00:00",
            last_signal_at="2026-07-31T00:00:00+00:00",
            signal_count=1,
            accumulated_depth=depth,
            last_depth_delta=depth,
            existence_confirmed=existence,
            coarse_mass_estimate=estimate,
            mass_confidence=confidence,
            quarantine=quarantine,
            sender_emergent_mass=sender_emergent_mass,
            sender_emergent_mass_at=(
                "2026-07-31T00:00:00+00:00" if sender_emergent_mass is not None else None
            ),
        )
        self.store.save_foreign(rec)

    def test_empty_zone_unobserved(self):
        out = compute_mass_readout(self.registry)
        self.assertIsNone(out.emergent_self_mass)
        self.assertEqual(out.volume_count, 0)
        self.assertEqual(out.estimator_count, 0)

    def test_existence_only_no_self_mass(self):
        self._save_estimate("alice", estimate=None, depth=0.5, sender_emergent_mass=40)
        out = compute_mass_readout(self.registry)
        self.assertIsNone(out.emergent_self_mass)
        self.assertEqual(out.volume_count, 1)
        self.assertEqual(out.estimator_count, 0)

    def test_single_estimator_equals_estimate(self):
        self._save_estimate(
            "alice", estimate=70, confidence=1.0, depth=1.0, sender_emergent_mass=50
        )
        out = compute_mass_readout(self.registry)
        self.assertIsNotNone(out.emergent_self_mass)
        assert out.emergent_self_mass is not None
        self.assertAlmostEqual(out.emergent_self_mass, 70.0)
        self.assertEqual(out.estimator_count, 1)
        self.assertEqual(out.contributors[0].sender_mass_source, "signal")

    def test_weighted_mean_by_sender_emergent_mass(self):
        # High emergent-Mass sender says 80; low says 20 → closer to 80
        self._save_estimate(
            "heavy", estimate=80, confidence=1.0, depth=1.0, sender_emergent_mass=90
        )
        self._save_estimate(
            "light", estimate=20, confidence=1.0, depth=1.0, sender_emergent_mass=10
        )
        out = compute_mass_readout(self.registry)
        self.assertIsNotNone(out.emergent_self_mass)
        assert out.emergent_self_mass is not None
        self.assertGreater(out.emergent_self_mass, 50.0)
        self.assertLess(out.emergent_self_mass, 80.0)

        w_h = weight_for(sender_mass=90, confidence=1.0, accumulated_depth=1.0)
        w_l = weight_for(sender_mass=10, confidence=1.0, accumulated_depth=1.0)
        expected = (w_h * 80 + w_l * 20) / (w_h + w_l)
        self.assertAlmostEqual(out.emergent_self_mass, expected)

    def test_registry_my_mass_estimate_is_ignored(self):
        # Even if local Registry claims the sender is massive, weighting uses
        # sender_emergent_mass from the signal only.
        import json

        peer = self.registry / "alice.json"
        peer.write_text(
            json.dumps({"local_handle": "alice", "my_mass_estimate": 99}),
            encoding="utf-8",
        )
        self._save_estimate(
            "alice", estimate=40, confidence=1.0, depth=1.0, sender_emergent_mass=10
        )
        out = compute_mass_readout(self.registry)
        contrib = [c for c in out.contributors if c.included][0]
        self.assertEqual(contrib.sender_mass, 10.0)
        self.assertEqual(contrib.sender_mass_source, "signal")

    def test_quarantine_excluded(self):
        self._save_estimate(
            "alice", estimate=90, confidence=1.0, depth=1.0, sender_emergent_mass=50
        )
        self._save_estimate(
            "bob",
            estimate=10,
            confidence=1.0,
            depth=1.0,
            quarantine=True,
            sender_emergent_mass=50,
        )
        out = compute_mass_readout(self.registry)
        self.assertAlmostEqual(out.emergent_self_mass or -1, 90.0)
        self.assertEqual(out.estimator_count, 1)
        self.assertEqual(out.volume_count, 1)

    def test_missing_sender_mass_uses_m_unknown(self):
        self._save_estimate("stranger", estimate=40, confidence=1.0, depth=1.0)
        out = compute_mass_readout(self.registry)
        self.assertAlmostEqual(out.emergent_self_mass or -1, 40.0)
        contrib = [c for c in out.contributors if c.included][0]
        self.assertEqual(contrib.sender_mass, M_UNKNOWN)
        self.assertEqual(contrib.sender_mass_source, "cold_start")

    def test_public_card_includes_mass(self):
        self._save_estimate(
            "alice", estimate=55, confidence=1.0, depth=1.0, sender_emergent_mass=40
        )
        card = build_public_card(
            local_handle="me",
            registry_root=self.registry,
            preferred_name="Me",
        )
        self.assertEqual(card["local_handle"], "me")
        self.assertAlmostEqual(card["emergent_self_mass"], 55.0)
        self.assertFalse(card["mass_unobserved"])
        self.assertEqual(card["volume_count"], 1)
        self.assertEqual(card["estimator_count"], 1)

    def test_public_card_unobserved(self):
        card = build_public_card(local_handle="me", registry_root=self.registry)
        self.assertIsNone(card["emergent_self_mass"])
        self.assertTrue(card["mass_unobserved"])


if __name__ == "__main__":
    unittest.main()
