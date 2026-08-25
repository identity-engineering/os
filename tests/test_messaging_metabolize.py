"""Tests for message metabolization."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from runtime.database import initialize_database
from runtime.messaging import register_card, send_envelope
from runtime.messaging_metabolize import get_metabolization, metabolize_message

ID_A = "018f3a2b-7c9e-7d01-8a2b-000000000001"
ID_B = "018f3a2b-7c9e-7d01-8a2b-000000000002"


def _card(identity_id: str, name: str) -> dict:
    return {
        "identityId": identity_id,
        "name": name,
        "type": "agent",
        "version": "0.1",
        "endpoints": {"messaging": "http://127.0.0.1:7420/messaging"},
        "recognitionPolicy": {"default": "accept-all"},
    }


class MetabolizeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".ie").mkdir()
        register_card(self.root, _card(ID_B, "bob"))
        result = send_envelope(
            self.root,
            {
                "from": ID_A,
                "to": ID_B,
                "signal": {"type": "task"},
                "payload": {"contentType": "text/plain", "inline": "do the thing"},
            },
        )
        self.assertEqual(result.status, "delivered")
        self.message_id = result.envelope["messageId"]

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_metabolize_records_and_receipt(self) -> None:
        out = metabolize_message(
            self.root,
            self.message_id,
            notes="integrated task",
            classification="task-accepted",
        )
        self.assertEqual(out["status"], "metabolized")
        self.assertEqual(out["record"]["classification"], "task-accepted")
        self.assertIsNotNone(out["receipt"])
        self.assertEqual(out["receipt"]["receiptType"], "metabolized")

        again = metabolize_message(self.root, self.message_id)
        self.assertEqual(again["status"], "already-metabolized")

        stored = get_metabolization(self.root, self.message_id)
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertEqual(stored["notes"], "integrated task")

    def test_metabolize_with_mature(self) -> None:
        # Full IE install for Mature path
        install = self.root / "ie-install"
        initialize_database(install, handle="me", preferred_name="Me")
        register_card(install, _card(ID_B, "bob"))
        result = send_envelope(
            install,
            {
                "from": ID_A,
                "to": ID_B,
                "signal": {"type": "insight"},
                "payload": {"contentType": "text/plain", "inline": "geometry shift"},
            },
        )
        mid = result.envelope["messageId"]
        out = metabolize_message(
            install,
            mid,
            notes="message became learning",
            commit_mature=True,
        )
        self.assertEqual(out["status"], "metabolized")
        self.assertIsNotNone(out["record"]["matureId"])
        self.assertIsNotNone(out["mature"])
        evidence = install / "trajectory" / "messaging" / f"{mid}.json"
        self.assertTrue(evidence.is_file())


if __name__ == "__main__":
    unittest.main()
