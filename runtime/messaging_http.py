"""Thin local HTTP surface for Identity-Native Messaging.

Stdlib only. Parallel to runtime.http_handler (Interaction Signals).

    python -m runtime.messaging_http --install path/to/install --port 7420

Routes:

- GET  /ie/v0/messaging/health
- GET  /ie/v0/messaging/cards
- GET  /ie/v0/messaging/cards/<identityId>
- POST /ie/v0/messaging/cards
- POST /ie/v0/messaging/messages
- GET  /ie/v0/messaging/inbox
- GET  /ie/v0/messaging/messages/<messageId>
- GET  /ie/v0/messaging/agent-card/<identityId>
- POST /ie/v0/messaging/import-agent-card
- GET  /.well-known/agent-card.json  (primary card if configured)
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from .a2a_adapter import agent_card_to_identity_card, identity_card_to_agent_card
from .messaging import (
    MessagingError,
    get_card,
    get_message,
    list_cards,
    list_inbox,
    register_card,
    send_envelope,
)


class MessagingHTTPServer(HTTPServer):
    def __init__(
        self,
        server_address,
        install_root: Path,
        primary_identity_id: Optional[str] = None,
    ):
        super().__init__(server_address, _make_handler())
        self.install_root = install_root
        self.primary_identity_id = primary_identity_id


def _make_handler():
    class Handler(BaseHTTPRequestHandler):
        server: MessagingHTTPServer

        def log_message(self, fmt: str, *args) -> None:
            print(f"[messaging] {self.address_string()} - {fmt % args}")

        def _send_json(self, code: int, body: dict | list) -> None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _read_json_body(self) -> tuple[Optional[dict], Optional[str]]:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return None, "invalid JSON"
            if not isinstance(payload, dict):
                return None, "expected JSON object"
            return payload, None

        def _public_base(self) -> str:
            host = self.headers.get("Host") or f"127.0.0.1:{self.server.server_address[1]}"
            return f"http://{host}"

        def do_GET(self) -> None:
            path = urlparse(self.path).path.rstrip("/") or "/"
            root = self.server.install_root

            if path == "/ie/v0/messaging/health":
                self._send_json(
                    200,
                    {
                        "status": "ok",
                        "surface": "ie-os-messaging-v0",
                        "install": str(root),
                    },
                )
                return

            if path in ("/.well-known/agent-card.json", "/.well-known/agent-card"):
                primary = self.server.primary_identity_id
                if not primary:
                    cards = list_cards(root)
                    if len(cards) == 1:
                        primary = cards[0].get("identityId")
                if not primary:
                    self._send_json(
                        404,
                        {
                            "error": "no primary Identity Card; pass --identity or register exactly one card"
                        },
                    )
                    return
                card = get_card(root, primary)
                if card is None:
                    self._send_json(404, {"error": "primary card not found"})
                    return
                try:
                    agent = identity_card_to_agent_card(
                        card,
                        messaging_base_url=f"{self._public_base()}/ie/v0/messaging",
                    )
                except MessagingError as exc:
                    self._send_json(400, {"error": str(exc)})
                    return
                self._send_json(200, agent)
                return

            if path == "/ie/v0/messaging/cards":
                self._send_json(200, {"cards": list_cards(root)})
                return

            if path.startswith("/ie/v0/messaging/agent-card/"):
                identity_id = path[len("/ie/v0/messaging/agent-card/") :]
                card = get_card(root, identity_id)
                if card is None:
                    self._send_json(404, {"error": "card not found"})
                    return
                try:
                    agent = identity_card_to_agent_card(
                        card,
                        messaging_base_url=f"{self._public_base()}/ie/v0/messaging",
                    )
                except MessagingError as exc:
                    self._send_json(400, {"error": str(exc)})
                    return
                self._send_json(200, agent)
                return

            if path.startswith("/ie/v0/messaging/cards/"):
                identity_id = path[len("/ie/v0/messaging/cards/") :]
                card = get_card(root, identity_id)
                if card is None:
                    self._send_json(404, {"error": "card not found"})
                    return
                self._send_json(200, card)
                return

            if path == "/ie/v0/messaging/inbox":
                self._send_json(200, {"messages": list_inbox(root)})
                return

            if path.startswith("/ie/v0/messaging/messages/"):
                message_id = path[len("/ie/v0/messaging/messages/") :]
                msg = get_message(root, message_id)
                if msg is None:
                    self._send_json(404, {"error": "message not found"})
                    return
                self._send_json(200, msg)
                return

            self._send_json(404, {"error": "not found"})

        def do_POST(self) -> None:
            path = urlparse(self.path).path.rstrip("/") or "/"
            root = self.server.install_root
            body, err = self._read_json_body()
            if err:
                self._send_json(400, {"error": err})
                return
            assert body is not None

            if path == "/ie/v0/messaging/cards":
                try:
                    stored = register_card(root, body)
                except MessagingError as exc:
                    self._send_json(400, {"error": str(exc)})
                    return
                self._send_json(201, stored)
                return

            if path == "/ie/v0/messaging/import-agent-card":
                try:
                    card = agent_card_to_identity_card(body)
                    stored = register_card(root, card)
                except MessagingError as exc:
                    self._send_json(400, {"error": str(exc)})
                    return
                self._send_json(201, stored)
                return

            if path == "/ie/v0/messaging/messages":
                try:
                    result = send_envelope(root, body)
                except MessagingError as exc:
                    self._send_json(400, {"error": str(exc)})
                    return
                code = 200 if result.status == "delivered" else 422
                self._send_json(code, result.to_dict())
                return

            self._send_json(404, {"error": "not found"})

    return Handler


def serve(
    install_root: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 7420,
    primary_identity_id: Optional[str] = None,
) -> None:
    httpd = MessagingHTTPServer(
        (host, port),
        install_root=install_root,
        primary_identity_id=primary_identity_id,
    )
    print(f"IE OS messaging surface on http://{host}:{port}")
    print(f"  GET  /ie/v0/messaging/health")
    print(f"  GET  /ie/v0/messaging/cards")
    print(f"  POST /ie/v0/messaging/cards")
    print(f"  POST /ie/v0/messaging/messages")
    print(f"  GET  /ie/v0/messaging/inbox")
    print(f"  GET  /ie/v0/messaging/agent-card/<id>")
    print(f"  POST /ie/v0/messaging/import-agent-card")
    print(f"  GET  /.well-known/agent-card.json")
    print(f"  install: {install_root}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
        httpd.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="IE OS local messaging HTTP surface (v0)"
    )
    parser.add_argument(
        "--install",
        dest="install_root",
        required=True,
        help="Path to the IE install root",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7420)
    parser.add_argument(
        "--identity",
        dest="primary_identity_id",
        default=None,
        help="Primary identityId for /.well-known/agent-card.json",
    )
    args = parser.parse_args(argv)

    serve(
        Path(args.install_root),
        host=args.host,
        port=args.port,
        primary_identity_id=args.primary_identity_id,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
