"""Thin local HTTP surface that re-uses apply_interaction_signal.

Stdlib only. Suitable for Free-tier dogfood:

    python -m runtime.http_handler --registry path/to/registry --to my-handle --port 8787

Routes (aligned with schemas/surface-operations/v0.yaml):

- POST /ie/v0/signals  → receive_interaction_signal
- GET  /ie/v0/card     → get_public_card (minimal)
- GET  /ie/v0/health   → liveness
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from .apply import apply_from_dict
from .policy import LocalPolicy


class SurfaceHTTPServer(HTTPServer):
    def __init__(
        self,
        server_address,
        registry_root: Path,
        to_handle: str,
        policy: LocalPolicy,
        preferred_name: Optional[str] = None,
    ):
        super().__init__(server_address, _make_handler())
        self.registry_root = registry_root
        self.to_handle = to_handle
        self.policy = policy
        self.preferred_name = preferred_name


def _make_handler():
    class Handler(BaseHTTPRequestHandler):
        server: SurfaceHTTPServer  # type narrowing

        def log_message(self, fmt: str, *args) -> None:
            # quieter default logging
            print(f"[surface] {self.address_string()} - {fmt % args}")

        def _send_json(self, code: int, body: dict) -> None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            path = urlparse(self.path).path.rstrip("/") or "/"
            if path == "/ie/v0/health":
                self._send_json(200, {"status": "ok", "surface": "ie-os-local-v0"})
                return
            if path == "/ie/v0/card":
                card = {
                    "local_handle": self.server.to_handle,
                    "preferred_name": self.server.preferred_name,
                    "substrate": "human",
                    "accepts_ie_signals": True,
                    "schema_version": "0",
                }
                self._send_json(200, card)
                return
            self._send_json(404, {"error": "not found"})

        def do_POST(self) -> None:
            path = urlparse(self.path).path.rstrip("/") or "/"
            if path != "/ie/v0/signals":
                self._send_json(404, {"error": "not found"})
                return

            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                self._send_json(400, {"error": "invalid JSON"})
                return

            # Ensure transport meta
            if "transport" not in payload:
                payload["transport"] = "http"

            receipt = apply_from_dict(
                payload,
                registry_root=self.server.registry_root,
                policy=self.server.policy,
                expected_to_handle=self.server.to_handle,
            )
            code = 200 if receipt.status.value in ("applied", "partial", "accepted") else 400
            self._send_json(code, receipt.to_dict())

    return Handler


def serve(
    registry_root: Path,
    to_handle: str,
    *,
    host: str = "127.0.0.1",
    port: int = 8787,
    open_consent: bool = False,
    preferred_name: Optional[str] = None,
) -> None:
    policy = LocalPolicy(open_consent=open_consent)
    httpd = SurfaceHTTPServer(
        (host, port),
        registry_root=registry_root,
        to_handle=to_handle,
        policy=policy,
        preferred_name=preferred_name,
    )
    print(f"IE OS local surface on http://{host}:{port}")
    print(f"  POST /ie/v0/signals   (receive_interaction_signal)")
    print(f"  GET  /ie/v0/card      (public card)")
    print(f"  GET  /ie/v0/health")
    print(f"  registry: {registry_root}")
    print(f"  to_handle: {to_handle}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
        httpd.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IE OS local HTTP surface (v0)")
    parser.add_argument("--registry", required=True, help="Path to registry/ directory")
    parser.add_argument("--to", required=True, help="This surface's handle")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--open-consent", action="store_true")
    parser.add_argument("--name", help="preferred_name for public card")
    args = parser.parse_args(argv)

    serve(
        Path(args.registry),
        args.to,
        host=args.host,
        port=args.port,
        open_consent=args.open_consent,
        preferred_name=args.name,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
