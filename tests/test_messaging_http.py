"""Tests for Identity-Native Messaging HTTP surface."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.client import HTTPConnection
from pathlib import Path

from runtime.messaging_http import MessagingHTTPServer

ID_A = "018f3a2b-7c9e-7d01-8a2b-000000000001"
ID_B = "018f3a2b-7c9e-7d01-8a2b-000000000002"


def _card(identity_id: str, name: str = "test") -> dict:
    return {
        "identityId": identity_id,
        "name": name,
        "type": "agent",
        "version": "0.1",
        "endpoints": {"messaging": "http://127.0.0.1:7420/messaging"},
        "recognitionPolicy": {"default": "accept-all"},
    }


class MessagingHTTPTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / ".ie").mkdir()
        # Bind ephemeral port
        self.httpd = MessagingHTTPServer(("127.0.0.1", 0), install_root=self.root)
        self.port = self.httpd.server_address[1]
        self._thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self._thread.start()

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self._tmp.cleanup()

    def _request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
    ) -> tuple[int, dict]:
        conn = HTTPConnection("127.0.0.1", self.port, timeout=5)
        data = None
        headers = {}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
            headers["Content-Length"] = str(len(data))
        conn.request(method, path, body=data, headers=headers)
        resp = conn.getresponse()
        raw = resp.read().decode("utf-8")
        conn.close()
        return resp.status, json.loads(raw)

    def test_health(self) -> None:
        status, body = self._request("GET", "/ie/v0/messaging/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")

    def test_register_card_and_list(self) -> None:
        status, card = self._request("POST", "/ie/v0/messaging/cards", _card(ID_A, "alice"))
        self.assertEqual(status, 201)
        self.assertEqual(card["identityId"], ID_A)

        status, listing = self._request("GET", "/ie/v0/messaging/cards")
        self.assertEqual(status, 200)
        self.assertEqual(len(listing["cards"]), 1)

        status, one = self._request("GET", f"/ie/v0/messaging/cards/{ID_A}")
        self.assertEqual(status, 200)
        self.assertEqual(one["name"], "alice")

    def test_send_and_inbox(self) -> None:
        self._request("POST", "/ie/v0/messaging/cards", _card(ID_B, "bob"))
        status, result = self._request(
            "POST",
            "/ie/v0/messaging/messages",
            {
                "from": ID_A,
                "to": ID_B,
                "signal": {"type": "message"},
                "payload": {"contentType": "text/plain", "inline": "hi"},
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(result["status"], "delivered")

        status, inbox = self._request("GET", "/ie/v0/messaging/inbox")
        self.assertEqual(status, 200)
        self.assertEqual(len(inbox["messages"]), 1)

        mid = result["envelope"]["messageId"]
        status, msg = self._request("GET", f"/ie/v0/messaging/messages/{mid}")
        self.assertEqual(status, 200)
        self.assertEqual(msg["messageId"], mid)

    def test_send_rejected_unknown_target(self) -> None:
        status, result = self._request(
            "POST",
            "/ie/v0/messaging/messages",
            {
                "from": ID_A,
                "to": ID_B,
                "signal": {"type": "message"},
                "payload": {"contentType": "text/plain", "inline": "hi"},
            },
        )
        self.assertEqual(status, 422)
        self.assertEqual(result["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
