"""Unit tests for Geometry Receipt extractors + always-on apply hook."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from runtime.apply import apply_from_dict
from runtime.geometry import (
    GeometryReceiptStore,
    extract_depth_mass,
    extract_membrane_policy,
    run_geometry_hook,
)
from runtime.models import ApplyStatus, InteractionSignal, Receipt
from runtime.policy import LocalPolicy


class GeometryExtractorTests(unittest.TestCase):
    def _signal(self, **overrides) -> InteractionSignal:
        base = dict(
            from_handle="alice",
            to_handle="bob",
            timestamp="2026-08-02T00:00:00+00:00",
            existence=True,
            interaction_depth_delta=0.4,
        )
        base.update(overrides)
        return InteractionSignal(**base)

    def _receipt(
        self,
        *,
        applied: list[str] | None = None,
        rejected: list[dict[str, str]] | None = None,
        status: ApplyStatus = ApplyStatus.APPLIED,
    ) -> Receipt:
        return Receipt.create(
            status,
            "alice",
            "bob",
            applied=applied
            or ["existence", "interaction_depth_delta", "sender_emergent_mass"],
            rejected=rejected or [],
        )

    def test_mass_proxy_prefers_signal_sender_emergent_mass(self):
        signal = self._signal(sender_emergent_mass=42.0)
        receipt = self._receipt()
        out = extract_depth_mass(signal, receipt, {})
        self.assertIsNotNone(out.get("relative_mass_proxy"))
        proxy = out["relative_mass_proxy"]
        self.assertAlmostEqual(proxy["value"], 42.0)
        self.assertIn("signal.sender_emergent_mass", proxy["notes"])
        # Must not confuse with Self-Mass of observer
        self.assertIn("Not Self-Mass", proxy["notes"])

    def test_mass_proxy_falls_back_to_stored_then_public_card(self):
        signal = self._signal(sender_emergent_mass=None)
        receipt = self._receipt(
            applied=["existence", "interaction_depth_delta"],
        )
        stored = extract_depth_mass(
            signal, receipt, {"sender_emergent_mass": 55.0}
        )
        self.assertAlmostEqual(stored["relative_mass_proxy"]["value"], 55.0)
        self.assertIn("stored", stored["relative_mass_proxy"]["notes"])

        card = extract_depth_mass(
            signal, receipt, {"public_card_emergent_self_mass": 61.0}
        )
        self.assertAlmostEqual(card["relative_mass_proxy"]["value"], 61.0)
        self.assertIn("public_card", card["relative_mass_proxy"]["notes"])

    def test_mass_proxy_never_uses_coarse_estimate_of_observer(self):
        # coarse_mass_estimate is "their view of me" — not their Mass
        signal = self._signal(
            sender_emergent_mass=None,
            coarse_mass_estimate=99.0,
            mass_confidence=0.9,
        )
        receipt = self._receipt(
            applied=[
                "existence",
                "interaction_depth_delta",
                "coarse_mass_estimate",
                "mass_confidence",
            ],
        )
        out = extract_depth_mass(signal, receipt, {})
        proxy = out["relative_mass_proxy"]
        # Depth-only placeholder, not 99
        self.assertNotAlmostEqual(proxy["value"], 99.0)
        self.assertIn("depth-only", proxy["notes"])
        self.assertLess(proxy["confidence"], 0.3)

    def test_membrane_policy_observational_no_access_claim(self):
        signal = self._signal(coarse_mass_estimate=30.0, mass_confidence=0.5)
        receipt = self._receipt(
            status=ApplyStatus.PARTIAL,
            applied=["existence", "interaction_depth_delta"],
            rejected=[
                {"field": "coarse_mass_estimate", "reason": "no grant"},
                {"field": "mass_confidence", "reason": "no grant"},
            ],
        )
        out = extract_membrane_policy(signal, receipt, {})
        shift = out["jurisdiction_shift"]
        self.assertEqual(shift["access_delta"], 0.0)
        self.assertEqual(shift["jurisdiction_delta"], 0.0)
        self.assertIn("#40", shift["notes"])
        self.assertIn("consent_rejected", shift["notes"])

    def test_hook_rejected_apply_returns_none(self):
        signal = self._signal()
        receipt = Receipt.create(
            ApplyStatus.REJECTED, "alice", "bob", reason="bad"
        )
        geo = run_geometry_hook(signal, receipt, observer="bob")
        self.assertIsNone(geo)

    def test_hook_records_extractor_errors_in_notes(self):
        signal = self._signal(sender_emergent_mass=10.0)
        receipt = self._receipt()

        def boom(_s, _r, _c=None):
            raise RuntimeError("extractor exploded")

        geo = run_geometry_hook(
            signal,
            receipt,
            observer="bob",
            extractors=(boom, extract_depth_mass),
        )
        assert geo is not None
        self.assertIn("extractor_errors=", geo.notes)
        self.assertIn("RuntimeError", geo.notes)
        # Other extractors still ran
        self.assertIsNotNone(geo.relative_mass_proxy)


class GeometryApplyHookTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.registry = Path(self._tmp.name) / "registry"
        self.registry.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _base(self, **overrides):
        p = {
            "from": "peer-alice",
            "to": "me",
            "timestamp": "2026-08-02T12:00:00+00:00",
            "existence": True,
            "interaction_depth_delta": 0.2,
            "sender_emergent_mass": 44.0,
        }
        p.update(overrides)
        return p

    def test_apply_default_emits_geometry_receipt(self):
        receipt = apply_from_dict(
            self._base(),
            registry_root=self.registry,
            expected_to_handle="me",
        )
        self.assertEqual(receipt.status, ApplyStatus.APPLIED)
        self.assertIn("geometry_receipt=", receipt.reason)

        store = GeometryReceiptStore(self.registry)
        ids = store.list_ids()
        self.assertEqual(len(ids), 1)
        data = store.load(ids[0])
        assert data is not None
        self.assertEqual(data["mode"], "interact")
        self.assertEqual(data["observer"], "me")
        self.assertEqual(data["target"], "peer-alice")
        self.assertAlmostEqual(data["relative_mass_proxy"]["value"], 44.0)
        self.assertEqual(data["source_signal_ref"], receipt.receipt_id)

    def test_emit_false_skips_geometry(self):
        receipt = apply_from_dict(
            self._base(),
            registry_root=self.registry,
            expected_to_handle="me",
            emit_geometry_receipt=False,
        )
        self.assertEqual(receipt.status, ApplyStatus.APPLIED)
        self.assertNotIn("geometry_receipt=", receipt.reason)
        store = GeometryReceiptStore(self.registry)
        self.assertEqual(store.list_ids(), [])

    def test_rejected_apply_no_geometry(self):
        receipt = apply_from_dict(
            self._base(to="someone-else"),
            registry_root=self.registry,
            expected_to_handle="me",
        )
        self.assertEqual(receipt.status, ApplyStatus.REJECTED)
        self.assertNotIn("geometry_receipt=", receipt.reason)
        store = GeometryReceiptStore(self.registry)
        # store root may not exist if never saved — list via path
        geo_dir = self.registry / "_geometry_receipts"
        if geo_dir.exists():
            self.assertEqual(list(geo_dir.iterdir()), [])

    def test_partial_consent_still_emits_with_membrane_stub(self):
        receipt = apply_from_dict(
            self._base(coarse_mass_estimate=50, mass_confidence=0.8),
            registry_root=self.registry,
            expected_to_handle="me",
            policy=LocalPolicy(open_consent=False),
        )
        self.assertEqual(receipt.status, ApplyStatus.PARTIAL)
        self.assertIn("geometry_receipt=", receipt.reason)
        store = GeometryReceiptStore(self.registry)
        data = store.load(store.list_ids()[0])
        assert data is not None
        self.assertEqual(data["jurisdiction_shift"]["access_delta"], 0.0)
        self.assertIn("#40", data["jurisdiction_shift"]["notes"])


if __name__ == "__main__":
    unittest.main()
