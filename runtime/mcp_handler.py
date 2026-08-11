"""Local MCP Surface binding (stdio JSON-RPC) — Identity-scoped.

Implements a minimal subset of the Model Context Protocol over newline-delimited
JSON-RPC 2.0 on stdin/stdout. Tools wrap the same runtime handlers as CLI/HTTP.

Session always authenticates as the install Identity and binds to an active
Space membership. Results include actor_identity_id and space_id. Capability
checks are repeated for every tool call; cross-Identity write is not exposed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional, TextIO

from ie.status_cmd import collect_status
from runtime.apply import apply_from_dict
from runtime.mass import build_public_card, compute_mass_readout
from runtime.mcp_session import IdentitySession, bind_local_session
from runtime.policy import LocalPolicy

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "ie-os-local"
SERVER_VERSION = "0"

TOOL_DEFS: list[dict[str, Any]] = [
    {
        "name": "ie_status",
        "description": (
            "Summarize the bound local Identity install (handle, peers, "
            "foreign estimates, schema). Always returns actor_identity_id."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "ie_card",
        "description": (
            "Public card for the bound Identity including emergent_self_mass "
            "and last_mature_at (derived / public fields only)."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "ie_mass",
        "description": (
            "Emergent self-Mass readout from the foreign-estimate zone. "
            "Derived only; never a self-declared Mass write."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "detail": {
                    "type": "boolean",
                    "description": "Include contributor breakdown",
                    "default": False,
                }
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "ie_signal_apply",
        "description": (
            "Apply an Interaction Signal into the bound Identity's foreign-estimate "
            "zone (same path as CLI/HTTP). to_handle must match the bound Identity."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "signal": {
                    "type": "object",
                    "description": "Interaction Signal payload (from, to, depth, estimates, …)",
                },
                "open_consent": {
                    "type": "boolean",
                    "description": "If true, consent-gated fields apply without grants (dev/dogfood)",
                    "default": False,
                },
            },
            "required": ["signal"],
            "additionalProperties": False,
        },
    },
    {
        "name": "ie_registry_list",
        "description": "List Registry peer handles for the bound Identity.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]


class McpSurface:
    def __init__(self, session: IdentitySession):
        self.session = session

    def call_tool(self, name: str, arguments: Optional[dict[str, Any]]) -> dict[str, Any]:
        args = arguments or {}
        if name == "ie_status":
            self.session.require_capability("surface")
            return self._status()
        if name == "ie_card":
            self.session.require_capability("surface")
            self.session.require_capability("public_card")
            return self._card()
        if name == "ie_mass":
            self.session.require_capability("surface")
            return self._mass(detail=bool(args.get("detail", False)))
        if name == "ie_signal_apply":
            self.session.require_capability("surface")
            self.session.require_capability("interaction_signal")
            signal = args.get("signal")
            if not isinstance(signal, dict):
                raise ValueError("ie_signal_apply requires signal object")
            return self._signal_apply(signal, open_consent=bool(args.get("open_consent", False)))
        if name == "ie_registry_list":
            self.session.require_capability("surface")
            return self._registry_list()
        raise ValueError(f"unknown tool: {name}")

    def _status(self) -> dict[str, Any]:
        info = collect_status(self.session.install_root)
        info["identity_id"] = self.session.identity_id
        return self.session.with_actor(info)

    def _card(self) -> dict[str, Any]:
        card = build_public_card(
            local_handle=self.session.local_handle,
            registry_root=self.session.install_root,
            preferred_name=self.session.preferred_name,
            substrate=self.session.substrate,
        )
        card["identity_id"] = self.session.identity_id
        return self.session.with_actor(card)

    def _mass(self, *, detail: bool) -> dict[str, Any]:
        readout = compute_mass_readout(self.session.install_root)
        body = readout.to_dict()
        if not detail:
            body.pop("contributors", None)
        body["identity_id"] = self.session.identity_id
        return self.session.with_actor(body)

    def _signal_apply(self, signal: dict[str, Any], *, open_consent: bool) -> dict[str, Any]:
        payload = dict(signal)
        if "transport" not in payload:
            payload["transport"] = "mcp"
        # Force destination to bound Identity — no cross-Identity apply via this tool.
        payload["to"] = self.session.local_handle
        payload["to_handle"] = self.session.local_handle

        policy = LocalPolicy(open_consent=True) if open_consent else None
        receipt = apply_from_dict(
            payload,
            registry_root=self.session.install_root,
            policy=policy,
            expected_to_handle=self.session.local_handle,
            observer_handle=self.session.local_handle,
        )
        body = receipt.to_dict()
        body["identity_id"] = self.session.identity_id
        return self.session.with_actor(body)

    def _registry_list(self) -> dict[str, Any]:
        peers = collect_status(self.session.install_root).get("registry_peers") or []
        return self.session.with_actor(
            {
                "identity_id": self.session.identity_id,
                "peers": list(peers),
            }
        )


def _tool_result(payload: dict[str, Any], *, is_error: bool = False) -> dict[str, Any]:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    return {
        "content": [{"type": "text", "text": text}],
        "structuredContent": payload,
        "isError": is_error,
    }


def handle_rpc(surface: McpSurface, message: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Handle one JSON-RPC request; return response or None for notifications."""
    method = message.get("method")
    msg_id = message.get("id", None)
    params = message.get("params") or {}

    if msg_id is None and method:
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": SERVER_NAME,
                    "version": SERVER_VERSION,
                },
                "instructions": (
                    "IE OS local Surface. Session is bound to one Identity and "
                    "an active Space membership. Capability checks run per tool. "
                    "Tools write only that Identity's geometry. "
                    f"actor_identity_id={surface.session.identity_id}"
                ),
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {"tools": TOOL_DEFS},
        }

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        try:
            if not name:
                raise ValueError("tools/call requires name")
            result = surface.call_tool(str(name), arguments if isinstance(arguments, dict) else {})
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": _tool_result(result, is_error=False),
            }
        except Exception as exc:  # noqa: BLE001 — surface error to MCP client
            err_payload = surface.session.with_actor(
                {"error": str(exc), "error_type": type(exc).__name__}
            )
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": _tool_result(err_payload, is_error=True),
            }

    return {
        "jsonrpc": "2.0",
        "id": msg_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def serve_stdio(
    session: IdentitySession,
    *,
    stdin: TextIO = sys.stdin,
    stdout: TextIO = sys.stdout,
) -> int:
    surface = McpSurface(session)
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            err = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }
            stdout.write(json.dumps(err) + "\n")
            stdout.flush()
            continue

        if not isinstance(message, dict):
            continue

        response = handle_rpc(surface, message)
        if response is not None:
            stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            stdout.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="IE OS local MCP surface (Identity-scoped)")
    parser.add_argument(
        "--install",
        "--path",
        dest="install_root",
        help="Path to IE install root (default: active root / IE_ROOT)",
    )
    parser.add_argument(
        "--space-id",
        default=None,
        help="Space ID with an active local membership (default: primary local Space)",
    )
    args = parser.parse_args(argv)

    if args.install_root:
        root = Path(args.install_root)
    else:
        from ie.paths import require_ie_root

        root = require_ie_root()

    session = bind_local_session(root, space_id=args.space_id)
    return serve_stdio(session)


if __name__ == "__main__":
    raise SystemExit(main())
