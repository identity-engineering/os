"""Stdlib unit tests for Surface Runtime local apply path."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from runtime.apply import apply_from_dict, apply_interaction_signal
from runtime.models import ApplyStatus, InteractionSignal
from runtime.policy import LocalPolicy
from runtime.storage import ForeignEstimateStore


class ApplyTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.registry = Path(self._tmp.name) / "registry"
        self.registry.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _base_payload(self, **overrides):
        p = {
            "from": "peer-alice",
            "to": "me",
            "timestamp": "2026-07-28T12:00:00+00:00",
            "existence": True,
            "interaction_depth_delta": 0.2,
        }
        p.update(overrides)
        return p

    def test_always_passed_applies(self):
        receipt = apply_from_dict(
            self._base_payload(),
            registry_root=self.registry,
            expected_to_handle="me",
        )
        self.assertEqual(receipt.status, ApplyStatus.APPLIED)
        self.assertIn("existence", receipt.applied_fields)
        self.assertIn("interaction_depth_delta", receipt.applied_fields)
        self.assertEqual(receipt.rejected_fields, [])

        store = ForeignEstimateStore(self.registry)
        rec = store.load("peer-alice")
        self.assertIsNotNone(rec)
        assert rec is not None
        self.assertTrue(rec.existence_confirmed)
        self.assertEqual(rec.signal_count, 1)
        self.assertAlmostEqual(rec.accumulated_depth, 0.2)

    def test_consent_refused_without_grant(self):
        payload = self._base_payload(
            coarse_mass_estimate=55,
            mass_confidence=0.8,
        )
        receipt = apply_from_dict(
            payload,
            registry_root=self.registry,
            policy=LocalPolicy(open_consent=False),
            expected_to_handle="me",
        )
        self.assertEqual(receipt.status, ApplyStatus.PARTIAL)
        self.assertIn("existence", receipt.applied_fields)
        rejected_names = {r["field"] for r in receipt.rejected_fields}
        self.assertIn("coarse_mass_estimate", rejected_names)
        self.assertIn("mass_confidence", rejected_names)

        store = ForeignEstimateStore(self.registry)
        rec = store.load("peer-alice")
        self.assertIsNotNone(rec)
        assert rec is not None
        self.assertIsNone(rec.coarse_mass_estimate)

    def test_consent_applied_with_open_consent(self):
        payload = self._base_payload(
            coarse_mass_estimate=42,
            mass_confidence=0.7,
        )
        receipt = apply_from_dict(
            payload,
            registry_root=self.registry,
            policy=LocalPolicy(open_consent=True),
            expected_to_handle="me",
        )
        self.assertEqual(receipt.status, ApplyStatus.APPLIED)
        self.assertIn("coarse_mass_estimate", receipt.applied_fields)

        store = ForeignEstimateStore(self.registry)
        rec = store.load("peer-alice")
        assert rec is not None
        self.assertEqual(rec.coarse_mass_estimate, 42)
        self.assertEqual(rec.mass_confidence, 0.7)

    def test_quarantine_blocks_depth_and_consent(self):
        policy = LocalPolicy(quarantined_handles={"peer-alice"}, open_consent=True)
        payload = self._base_payload(coarse_mass_estimate=10)
        receipt = apply_from_dict(
            payload,
            registry_root=self.registry,
            policy=policy,
            expected_to_handle="me",
        )
        self.assertTrue(receipt.quarantine)
        self.assertIn("existence", receipt.applied_fields)
        rejected_names = {r["field"] for r in receipt.rejected_fields}
        self.assertIn("interaction_depth_delta", rejected_names)
        self.assertIn("coarse_mass_estimate", rejected_names)

    def test_to_handle_mismatch_rejects(self):
        receipt = apply_from_dict(
            self._base_payload(),
            registry_root=self.registry,
            expected_to_handle="other-handle",
        )
        self.assertEqual(receipt.status, ApplyStatus.REJECTED)
        self.assertIn("mismatch", receipt.reason)

    def test_invalid_depth_rejects(self):
        receipt = apply_from_dict(
            self._base_payload(interaction_depth_delta=1.5),
            registry_root=self.registry,
            expected_to_handle="me",
        )
        self.assertEqual(receipt.status, ApplyStatus.REJECTED)

    def test_accumulation_across_signals(self):
        policy = LocalPolicy(open_consent=True)
        for delta in (0.1, 0.2, 0.05):
            apply_from_dict(
                self._base_payload(interaction_depth_delta=delta),
                registry_root=self.registry,
                policy=policy,
                expected_to_handle="me",
            )
        store = ForeignEstimateStore(self.registry)
        rec = store.load("peer-alice")
        assert rec is not None
        self.assertEqual(rec.signal_count, 3)
        self.assertAlmostEqual(rec.accumulated_depth, 0.35)


if __name__ == "__main__":
    unittest.main()
