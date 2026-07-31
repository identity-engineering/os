"""Unit tests for emergent self-Mass aggregation."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from runtime.mass import (
    M_UNKNOWN,
    compute_mass_readout,
    depth_factor,
    weight_for,
)
from runtime.models import ForeignEstimateRecord
from runtime.storage import ForeignEstimateStore

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None


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
        self.registry = Path(self._tmp.name) / "registry"
        self.registry.mkdir()
        self.store = ForeignEstimateStore(self.registry)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _write_peer(self, handle: str, mass: float) -> None:
        data = {
            "local_handle": handle,
            "preferred_name": handle,
            "substrate": "human",
            "my_mass_estimate": mass,
            "interaction_depth": 0.5,
            "dimensions": [],
        }
        path = self.registry / f"{handle}.yaml"
        if yaml is not None:
            path.write_text(
                yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
                encoding="utf-8",
            )
        else:
            import json

            path.with_suffix(".json").write_text(
                json.dumps(data, indent=2), encoding="utf-8"
            )

    def _save_estimate(
        self,
        handle: str,
        *,
        estimate: float | None,
        confidence: float | None = 0.8,
        depth: float = 1.0,
        quarantine: bool = False,
        existence: bool = True,
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
        )
        self.store.save(rec)

    def test_empty_zone_unobserved(self):
        out = compute_mass_readout(self.registry)
        self.assertIsNone(out.emergent_self_mass)
        self.assertEqual(out.volume_count, 0)
        self.assertEqual(out.estimator_count, 0)

    def test_existence_only_no_self_mass(self):
        self._save_estimate("alice", estimate=None, depth=0.5)
        out = compute_mass_readout(self.registry)
        self.assertIsNone(out.emergent_self_mass)
        self.assertEqual(out.volume_count, 1)
        self.assertEqual(out.estimator_count, 0)

    def test_single_estimator_equals_estimate(self):
        self._write_peer("alice", 50)
        self._save_estimate("alice", estimate=70, confidence=1.0, depth=1.0)
        out = compute_mass_readout(self.registry)
        self.assertIsNotNone(out.emergent_self_mass)
        assert out.emergent_self_mass is not None
        self.assertAlmostEqual(out.emergent_self_mass, 70.0)
        self.assertEqual(out.estimator_count, 1)

    def test_weighted_mean_two_senders(self):
        # Heavy peer says 80; light peer says 20 → result closer to 80
        self._write_peer("heavy", 90)
        self._write_peer("light", 10)
        self._save_estimate("heavy", estimate=80, confidence=1.0, depth=1.0)
        self._save_estimate("light", estimate=20, confidence=1.0, depth=1.0)
        out = compute_mass_readout(self.registry)
        self.assertIsNotNone(out.emergent_self_mass)
        assert out.emergent_self_mass is not None
        self.assertGreater(out.emergent_self_mass, 50.0)
        self.assertLess(out.emergent_self_mass, 80.0)

        w_h = weight_for(sender_mass=90, confidence=1.0, accumulated_depth=1.0)
        w_l = weight_for(sender_mass=10, confidence=1.0, accumulated_depth=1.0)
        expected = (w_h * 80 + w_l * 20) / (w_h + w_l)
        self.assertAlmostEqual(out.emergent_self_mass, expected)

    def test_quarantine_excluded(self):
        self._write_peer("alice", 50)
        self._write_peer("bob", 50)
        self._save_estimate("alice", estimate=90, confidence=1.0, depth=1.0)
        self._save_estimate(
            "bob", estimate=10, confidence=1.0, depth=1.0, quarantine=True
        )
        out = compute_mass_readout(self.registry)
        self.assertAlmostEqual(out.emergent_self_mass or -1, 90.0)
        self.assertEqual(out.estimator_count, 1)
        self.assertEqual(out.volume_count, 1)  # bob quarantined → not in volume

    def test_unknown_sender_uses_m_unknown(self):
        self._save_estimate("stranger", estimate=40, confidence=1.0, depth=1.0)
        out = compute_mass_readout(self.registry)
        self.assertIsNotNone(out.emergent_self_mass)
        assert out.emergent_self_mass is not None
        self.assertAlmostEqual(out.emergent_self_mass, 40.0)
        contrib = [c for c in out.contributors if c.included][0]
        self.assertEqual(contrib.sender_mass, M_UNKNOWN)
        self.assertEqual(contrib.sender_mass_source, "cold_start")


if __name__ == "__main__":
    unittest.main()
