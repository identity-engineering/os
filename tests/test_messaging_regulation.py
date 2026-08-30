"""Tests for collective Regulation routing and damping."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from runtime.messaging import (
    collect_messaging_status,
    list_inbox,
    register_card,
    send_envelope,
)

COLLECTIVE = "018f3a2b-7c9e-7d01-8a2b-0000000000c0"
SPEC_A = "018f3a2b-7c9e-7d01-8a2b-0000000000a1"
SPEC_B = "018f3a2b-7c9e-7d01-8a2b-0000000000a2"
SENDER = "018f3a2b-7c9e-7d01-8a2b-0000000000s1"


def _card(
    identity_id: str,
    name: str,
    *,
    type_: str = "agent",
    regulation: dict | None = None,
) -> dict:
    card: dict = {
        "identityId": identity_id,
        "name": name,
        "type": type_,
        "version": "0.1",
        "endpoints": {"messaging": "http://127.0.0.1:7420/messaging"},
        "recognitionPolicy": {"default": "accept-all"},
    }
    if regulation is not None:
        card["regulation"] = regulation
    return card


def _env(to: str) -> dict:
    return {
        "from": SENDER,
        "to": to,
        "signal": {"type": "message"},
        "payload": {"contentType": "text/plain", "inline": "coord"},
    }


class RegulationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".ie").mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_fan_out_delivers_to_specialists(self) -> None:
        register_card(self.root, _card(SPEC_A, "spec-a"))
        register_card(self.root, _card(SPEC_B, "spec-b"))
        register_card(
            self.root,
            _card(
                COLLECTIVE,
                "team",
                type_="collective",
                regulation={
                    "routing": "fan-out",
                    "specialists": [SPEC_A, SPEC_B],
                },
            ),
        )
        result = send_envelope(self.root, _env(COLLECTIVE))
        self.assertEqual(result.status, "delivered")
        targets = {d["target"] for d in result.deliveries if d["status"] == "delivered"}
        self.assertEqual(targets, {COLLECTIVE, SPEC_A, SPEC_B})
        # 1 original + 2 routed copies
        self.assertEqual(len(list_inbox(self.root)), 3)

    def test_specialist_routes_to_first_registered(self) -> None:
        register_card(self.root, _card(SPEC_A, "spec-a"))
        register_card(self.root, _card(SPEC_B, "spec-b"))
        register_card(
            self.root,
            _card(
                COLLECTIVE,
                "team",
                type_="collective",
                regulation={
                    "routing": "specialist",
                    "specialists": [SPEC_A, SPEC_B],
                },
            ),
        )
        result = send_envelope(self.root, _env(COLLECTIVE))
        self.assertEqual(result.status, "delivered")
        delivered = [d for d in result.deliveries if d["status"] == "delivered"]
        self.assertEqual(len(delivered), 1)
        self.assertEqual(delivered[0]["target"], SPEC_A)

    def test_central_only_collective(self) -> None:
        register_card(self.root, _card(SPEC_A, "spec-a"))
        register_card(
            self.root,
            _card(
                COLLECTIVE,
                "team",
                type_="collective",
                regulation={"routing": "central", "specialists": [SPEC_A]},
            ),
        )
        result = send_envelope(self.root, _env(COLLECTIVE))
        self.assertEqual(result.status, "delivered")
        self.assertEqual(
            [d["target"] for d in result.deliveries],
            [COLLECTIVE],
        )

    def test_damping_rejects_over_limit(self) -> None:
        register_card(
            self.root,
            _card(
                COLLECTIVE,
                "team",
                type_="collective",
                regulation={
                    "routing": "central",
                    "damping": {"maxMessagesPerWindow": 1, "windowSeconds": 3600},
                },
            ),
        )
        first = send_envelope(self.root, _env(COLLECTIVE))
        self.assertEqual(first.status, "delivered")
        status = collect_messaging_status(self.root)
        damping = status["damping"]["items"]
        self.assertEqual(len(damping), 1)
        self.assertEqual(damping[0]["currentCount"], 1)
        self.assertEqual(damping[0]["maxMessagesPerWindow"], 1)
        second = send_envelope(self.root, _env(COLLECTIVE))
        self.assertEqual(second.status, "rejected")
        self.assertIn("damping", second.receipt["reason"])
        status = collect_messaging_status(self.root)
        self.assertEqual(status["consent_audit"]["count"], 0)
        self.assertEqual(len(status["rejections"]), 1)
        self.assertEqual(status["rejections"][0]["reason"], second.receipt["reason"])


if __name__ == "__main__":
    unittest.main()
