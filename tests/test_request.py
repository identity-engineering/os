"""Stdlib unit tests for estimate request + inbox path."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from runtime.apply import apply_from_dict
from runtime.models import ApplyStatus, RequestStatus
from runtime.policy import LocalPolicy
from runtime.request import (
    RequestError,
    create_inbound_request,
    get_inbound_request,
    list_inbound_requests,
    set_request_status,
)
from runtime.storage import InboundRequestStore


class RequestTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.registry = Path(self._tmp.name) / "registry"
        self.registry.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_create_and_list_pending(self):
        req = create_inbound_request(
            registry_root=self.registry,
            requester_handle="alice",
            target_handle="me",
            requested_fields=["coarse_mass_estimate"],
            note="after workshop",
        )
        self.assertEqual(req.status, RequestStatus.PENDING)
        self.assertEqual(req.requester_handle, "alice")
        self.assertEqual(req.target_handle, "me")
        self.assertIn("coarse_mass_estimate", req.requested_fields)

        rows = list_inbound_requests(self.registry, status=RequestStatus.PENDING)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].request_id, req.request_id)

        loaded = get_inbound_request(self.registry, req.request_id)
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded.note, "after workshop")

    def test_ignore_and_quarantine(self):
        req = create_inbound_request(
            registry_root=self.registry,
            requester_handle="bob",
            target_handle="me",
        )
        ignored = set_request_status(
            self.registry, req.request_id, RequestStatus.IGNORED
        )
        self.assertEqual(ignored.status, RequestStatus.IGNORED)
        self.assertIsNotNone(ignored.ignored_at)

        req2 = create_inbound_request(
            registry_root=self.registry,
            requester_handle="carol",
            target_handle="me",
        )
        q = set_request_status(
            self.registry, req2.request_id, RequestStatus.QUARANTINED
        )
        self.assertEqual(q.status, RequestStatus.QUARANTINED)
        self.assertTrue(q.quarantine)

    def test_pending_rate_limit(self):
        for i in range(20):
            create_inbound_request(
                registry_root=self.registry,
                requester_handle="spammer",
                target_handle="me",
                request_id=f"r-{i}",
            )
        with self.assertRaises(RequestError):
            create_inbound_request(
                registry_root=self.registry,
                requester_handle="spammer",
                target_handle="me",
                request_id="r-overflow",
            )

    def test_reply_signal_marks_request_answered(self):
        req = create_inbound_request(
            registry_root=self.registry,
            requester_handle="alice",
            target_handle="me",
            requested_fields=["coarse_mass_estimate"],
        )
        payload = {
            "from": "me",
            "to": "alice",
            "timestamp": "2026-07-31T10:00:00+00:00",
            "existence": True,
            "interaction_depth_delta": 0.1,
            "coarse_mass_estimate": 60,
            "mass_confidence": 0.7,
            "in_reply_to_request_id": req.request_id,
        }
        # Reply is applied on the *requester's* surface in the real world.
        # For local unit test we apply into this same registry and still mark
        # the linked request answered (audit linkage is local to this store).
        receipt = apply_from_dict(
            payload,
            registry_root=self.registry,
            policy=LocalPolicy(open_consent=True),
            expected_to_handle="alice",
        )
        self.assertIn(receipt.status, (ApplyStatus.APPLIED, ApplyStatus.PARTIAL))

        updated = get_inbound_request(self.registry, req.request_id)
        self.assertIsNotNone(updated)
        assert updated is not None
        self.assertEqual(updated.status, RequestStatus.ANSWERED)
        self.assertEqual(updated.reply_receipt_id, receipt.receipt_id)
        self.assertIsNotNone(updated.answered_at)

    def test_store_roundtrip_yaml_or_json(self):
        store = InboundRequestStore(self.registry)
        req = create_inbound_request(
            registry_root=self.registry,
            requester_handle="dave",
            target_handle="me",
        )
        path = store.save(req)
        self.assertTrue(path.exists())
        again = store.load(req.request_id)
        self.assertIsNotNone(again)
        assert again is not None
        self.assertEqual(again.requester_handle, "dave")


if __name__ == "__main__":
    unittest.main()
