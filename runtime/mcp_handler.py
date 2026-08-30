"""Local MCP Surface binding (stdio JSON-RPC) — Identity-scoped.

Implements a minimal subset of the Model Context Protocol over newline-delimited
JSON-RPC 2.0 on stdin/stdout. Tools wrap the same runtime handlers as CLI/HTTP.

Session authenticates as one Identity (default: install active; optional
--identity-id / --handle). Results include actor_identity_id. Cross-Identity
write is not exposed in local tools.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional, TextIO

from ie.status_cmd import collect_status
from runtime.apply import apply_from_dict
from runtime.context import list_identities
from runtime.freedom import compute_freedom_readout
from runtime.grants import list_grants
from runtime.geometry_feed import feed_pending, feed_receipt
from runtime.mass import build_public_card, compute_mass_readout
from runtime.messaging import (
    collect_messaging_status,
    get_card,
    get_message,
    list_cards,
    list_inbox,
    register_card,
    send_envelope,
)
from runtime.messaging_metabolize import metabolize_message
from runtime.mcp_session import IdentitySession, bind_local_session
from runtime.models import RequestStatus
from runtime.policy import LocalPolicy
from runtime.request import list_inbound_requests

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "ie-os-local"
SERVER_VERSION = "1"

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
        "name": "ie_freedom",
        "description": (
            "Effective Freedom readout: unbound DoF / (1 + constraint intensity). "
            "Derived live; never a write."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "detail": {
                    "type": "boolean",
                    "description": "Include source component breakdown",
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
        "name": "ie_geometry_feed",
        "description": (
            "Feed Geometry Receipts into Registry effect_on_me (explicit path). "
            "Same semantics as `ie geometry feed`."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "receipt_id": {
                    "type": "string",
                    "description": "Feed one specific Geometry Receipt id",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max pending receipts when not targeting one id",
                    "default": 50,
                },
                "force": {
                    "type": "boolean",
                    "description": "Re-feed even if already marked fed",
                    "default": False,
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "ie_grants_list",
        "description": "List jurisdiction grants on the bound Identity.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "all": {
                    "type": "boolean",
                    "description": "Include revoked grants",
                    "default": False,
                }
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "ie_requests_list",
        "description": "List inbound estimate-request inbox items for the bound Identity.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "description": "Filter: pending|ignored|quarantined|answered|expired",
                }
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "ie_registry_list",
        "description": "List Registry peer handles for the bound Identity.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "ie_identity_list",
        "description": (
            "List Identities in this install. Marks session-bound Identity as "
            "active for this MCP process (not necessarily install.active). Read-only."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "ie_context_list",
        "description": (
            "List installed Context Layer documents for the bound Identity. "
            "Read-only; geometry remains in SQLite."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "ie_context_get",
        "description": (
            "Read one installed Context Layer document, such as the onboarding "
            "skill, for the bound Identity. Read-only."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Context document name, for example onboarding",
                }
            },
            "required": ["name"],
            "additionalProperties": False,
        },
    },
    {
        "name": "ie_messaging_cards",
        "description": "List locally registered Identity Messaging Cards.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "ie_messaging_status",
        "description": (
            "Show Messaging receipts, consent audit, metabolization status, "
            "damping windows, and explainable rejection reasons."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "ie_messaging_card",
        "description": "Read one locally registered public Messaging Card.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "identity_id": {"type": "string", "description": "Card identityId"}
            },
            "required": ["identity_id"],
            "additionalProperties": False,
        },
    },
    {
        "name": "ie_messaging_card_register",
        "description": (
            "Register the bound Identity's Messaging Card. identityId is always "
            "forced to the bound session Identity."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "card": {"type": "object", "description": "Messaging Card payload"}
            },
            "required": ["card"],
            "additionalProperties": False,
        },
    },
    {
        "name": "ie_messaging_inbox",
        "description": "Read Messaging Envelopes addressed to the bound Identity.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Optional maximum number of newest messages",
                }
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "ie_messaging_send",
        "description": (
            "Send a Messaging Envelope. The envelope from field is always forced "
            "to the bound Identity."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "envelope": {"type": "object", "description": "Messaging Envelope payload"}
            },
            "required": ["envelope"],
            "additionalProperties": False,
        },
    },
    {
        "name": "ie_messaging_metabolize",
        "description": (
            "Metabolize a message addressed to the bound receiving Identity, with "
            "an optional Mature commit."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "message_id": {"type": "string", "description": "Message ID"},
                "notes": {
                    "type": "string",
                    "description": "Processing notes",
                    "default": "",
                },
                "classification": {
                    "type": "string",
                    "description": "Optional classification label",
                },
                "mature": {
                    "type": "boolean",
                    "description": "Also commit a Mature step",
                    "default": False,
                },
            },
            "required": ["message_id"],
            "additionalProperties": False,
        },
    },
]


class McpSurface:
    def __init__(self, session: IdentitySession):
        self.session = session

    def call_tool(self, name: str, arguments: Optional[dict[str, Any]]) -> dict[str, Any]:
        args = arguments or {}
        if name == "ie_status":
            return self._status()
        if name == "ie_card":
            return self._card()
        if name == "ie_mass":
            return self._mass(detail=bool(args.get("detail", False)))
        if name == "ie_freedom":
            return self._freedom(detail=bool(args.get("detail", False)))
        if name == "ie_signal_apply":
            signal = args.get("signal")
            if not isinstance(signal, dict):
                raise ValueError("ie_signal_apply requires signal object")
            return self._signal_apply(signal, open_consent=bool(args.get("open_consent", False)))
        if name == "ie_geometry_feed":
            return self._geometry_feed(
                receipt_id=args.get("receipt_id"),
                limit=int(args.get("limit", 50)),
                force=bool(args.get("force", False)),
            )
        if name == "ie_grants_list":
            return self._grants_list(all_grants=bool(args.get("all", False)))
        if name == "ie_requests_list":
            return self._requests_list(status=args.get("status"))
        if name == "ie_registry_list":
            return self._registry_list()
        if name == "ie_identity_list":
            return self._identity_list()
        if name == "ie_context_list":
            return self._context_list()
        if name == "ie_context_get":
            context_name = args.get("name")
            if not isinstance(context_name, str):
                raise ValueError("ie_context_get requires name string")
            return self._context_get(context_name)
        if name == "ie_messaging_cards":
            return self._messaging_cards()
        if name == "ie_messaging_status":
            return self._messaging_status()
        if name == "ie_messaging_card":
            identity_id = args.get("identity_id")
            if not isinstance(identity_id, str) or not identity_id.strip():
                raise ValueError("ie_messaging_card requires identity_id string")
            return self._messaging_card(identity_id.strip())
        if name == "ie_messaging_card_register":
            card = args.get("card")
            if not isinstance(card, dict):
                raise ValueError("ie_messaging_card_register requires card object")
            return self._messaging_card_register(card)
        if name == "ie_messaging_inbox":
            return self._messaging_inbox(limit=args.get("limit"))
        if name == "ie_messaging_send":
            envelope = args.get("envelope")
            if not isinstance(envelope, dict):
                raise ValueError("ie_messaging_send requires envelope object")
            return self._messaging_send(envelope)
        if name == "ie_messaging_metabolize":
            message_id = args.get("message_id")
            if not isinstance(message_id, str) or not message_id.strip():
                raise ValueError("ie_messaging_metabolize requires message_id string")
            notes = args.get("notes", "")
            if not isinstance(notes, str):
                raise ValueError("ie_messaging_metabolize notes must be a string")
            classification = args.get("classification")
            if classification is not None and not isinstance(classification, str):
                raise ValueError(
                    "ie_messaging_metabolize classification must be a string"
                )
            return self._messaging_metabolize(
                message_id.strip(),
                notes=notes,
                classification=classification,
                mature=bool(args.get("mature", False)),
            )
        raise ValueError(f"unknown tool: {name}")

    def _status(self) -> dict[str, Any]:
        info = collect_status(self.session.install_root)
        info["identity_id"] = self.session.identity_id
        info["session_handle"] = self.session.local_handle
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

    def _freedom(self, *, detail: bool) -> dict[str, Any]:
        readout = compute_freedom_readout(self.session.install_root)
        body = readout.to_dict()
        if not detail:
            body.pop("sources", None)
        body["identity_id"] = self.session.identity_id
        return self.session.with_actor(body)

    def _signal_apply(self, signal: dict[str, Any], *, open_consent: bool) -> dict[str, Any]:
        payload = dict(signal)
        if "transport" not in payload:
            payload["transport"] = "mcp"
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

    def _geometry_feed(
        self,
        *,
        receipt_id: Optional[str],
        limit: int,
        force: bool,
    ) -> dict[str, Any]:
        root = self.session.install_root
        if receipt_id:
            result = feed_receipt(root, str(receipt_id), force=force)
        else:
            result = feed_pending(root, limit=max(1, limit), force=force)
        body = dict(result) if isinstance(result, dict) else {"result": result}
        body["identity_id"] = self.session.identity_id
        return self.session.with_actor(body)

    def _grants_list(self, *, all_grants: bool) -> dict[str, Any]:
        rows = list_grants(self.session.install_root, active_only=not all_grants)
        return self.session.with_actor(
            {
                "identity_id": self.session.identity_id,
                "grants": rows,
            }
        )

    def _requests_list(self, *, status: Optional[str]) -> dict[str, Any]:
        st_filter = None
        if status:
            try:
                st_filter = RequestStatus(str(status).strip().lower())
            except ValueError as exc:
                raise ValueError(
                    "status must be one of: pending|ignored|quarantined|answered|expired"
                ) from exc
        rows = list_inbound_requests(self.session.install_root, status=st_filter)
        return self.session.with_actor(
            {
                "identity_id": self.session.identity_id,
                "requests": [r.to_dict() for r in rows],
            }
        )

    def _registry_list(self) -> dict[str, Any]:
        peers = collect_status(self.session.install_root).get("registry_peers") or []
        return self.session.with_actor(
            {
                "identity_id": self.session.identity_id,
                "peers": list(peers),
            }
        )

    def _identity_list(self) -> dict[str, Any]:
        identities = list_identities(self.session.install_root)
        for item in identities:
            # "active" here means session-bound, not necessarily install.active
            item["active"] = item.get("identity_id") == self.session.identity_id
            item["session_bound"] = item["active"]
        return self.session.with_actor(
            {
                "identity_id": self.session.identity_id,
                "identities": identities,
            }
        )

    def _context_root(self) -> Path:
        return (self.session.install_root / "skills").resolve()

    def _context_path(self, name: str) -> Path:
        context_name = name.strip()
        if (
            not context_name
            or context_name in {".", ".."}
            or "/" in context_name
            or "\\" in context_name
        ):
            raise ValueError(f"invalid context name: {name!r}")

        install_root = self.session.install_root.resolve()
        path = (self._context_root() / context_name / "SKILL.md").resolve()
        try:
            path.relative_to(install_root)
        except ValueError as exc:
            raise ValueError("context path escapes install root") from exc
        return path

    def _context_list(self) -> dict[str, Any]:
        install_root = self.session.install_root.resolve()
        skills: list[dict[str, str]] = []
        root = self._context_root()
        if root.is_dir():
            for child in sorted(root.iterdir(), key=lambda item: item.name.lower()):
                if not child.is_dir():
                    continue
                skill_path = (child / "SKILL.md").resolve()
                if not skill_path.is_file():
                    continue
                try:
                    relative_path = skill_path.relative_to(install_root)
                except ValueError:
                    continue
                skills.append(
                    {
                        "name": child.name,
                        "source": "local_fs",
                        "path": relative_path.as_posix(),
                    }
                )
        return self.session.with_actor(
            {
                "identity_id": self.session.identity_id,
                "skills": skills,
            }
        )

    def _context_get(self, name: str) -> dict[str, Any]:
        path = self._context_path(name)
        if not path.is_file():
            raise ValueError(f"context document not found: {name}")
        return self.session.with_actor(
            {
                "identity_id": self.session.identity_id,
                "name": name.strip(),
                "source": "local_fs",
                "path": path.relative_to(self.session.install_root.resolve()).as_posix(),
                "body": path.read_text(encoding="utf-8"),
            }
        )

    @staticmethod
    def _message_targets_identity(message: dict[str, Any], identity_id: str) -> bool:
        target = message.get("to")
        if isinstance(target, str):
            return target == identity_id
        return isinstance(target, dict) and target.get("collectiveId") == identity_id

    def _messaging_cards(self) -> dict[str, Any]:
        return self.session.with_actor(
            {
                "identity_id": self.session.identity_id,
                "cards": list_cards(self.session.install_root),
            }
        )

    def _messaging_status(self) -> dict[str, Any]:
        body = collect_messaging_status(self.session.install_root)
        body["identity_id"] = self.session.identity_id
        return self.session.with_actor(body)

    def _messaging_card(self, identity_id: str) -> dict[str, Any]:
        card = get_card(self.session.install_root, identity_id)
        if card is None:
            raise ValueError(f"Messaging Card not found: {identity_id}")
        return self.session.with_actor(
            {
                "identity_id": self.session.identity_id,
                "card": card,
            }
        )

    def _messaging_card_register(self, card: dict[str, Any]) -> dict[str, Any]:
        payload = dict(card)
        payload["identityId"] = self.session.identity_id
        stored = register_card(self.session.install_root, payload)
        return self.session.with_actor(
            {
                "identity_id": self.session.identity_id,
                "card": stored,
            }
        )

    def _messaging_inbox(self, *, limit: Any = None) -> dict[str, Any]:
        resolved_limit: Optional[int] = None
        if limit is not None:
            try:
                resolved_limit = int(limit)
            except (TypeError, ValueError) as exc:
                raise ValueError("ie_messaging_inbox limit must be an integer") from exc
            if resolved_limit < 1:
                raise ValueError("ie_messaging_inbox limit must be at least 1")

        messages = [
            message
            for message in list_inbox(self.session.install_root)
            if self._message_targets_identity(message, self.session.identity_id)
        ]
        if resolved_limit is not None:
            messages = messages[:resolved_limit]
        return self.session.with_actor(
            {
                "identity_id": self.session.identity_id,
                "messages": messages,
            }
        )

    def _messaging_send(self, envelope: dict[str, Any]) -> dict[str, Any]:
        payload = dict(envelope)
        payload["from"] = self.session.identity_id
        result = send_envelope(self.session.install_root, payload)
        body = result.to_dict()
        body["identity_id"] = self.session.identity_id
        return self.session.with_actor(body)

    def _messaging_metabolize(
        self,
        message_id: str,
        *,
        notes: str,
        classification: Optional[str],
        mature: bool,
    ) -> dict[str, Any]:
        message = get_message(self.session.install_root, message_id)
        if message is None:
            raise ValueError(f"message not found: {message_id}")
        if not self._message_targets_identity(message, self.session.identity_id):
            raise ValueError("message is not addressed to the bound receiving Identity")
        result = metabolize_message(
            self.session.install_root,
            message_id,
            notes=notes,
            classification=classification,
            commit_mature=mature,
        )
        body = dict(result)
        body["identity_id"] = self.session.identity_id
        return self.session.with_actor(body)


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
                    "IE OS local Surface. Session is bound to one Identity. "
                    "Tools write only that Identity's geometry. "
                    f"actor_identity_id={surface.session.identity_id} "
                    f"handle={surface.session.local_handle}"
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
        help="Optional space_id stamp on actor envelope",
    )
    parser.add_argument(
        "--identity-id",
        default=None,
        help="Bind this local identity_id (default: install active Identity)",
    )
    parser.add_argument(
        "--handle",
        default=None,
        help="Bind this local_handle (default: install active Identity)",
    )
    args = parser.parse_args(argv)

    if args.install_root:
        root = Path(args.install_root)
    else:
        from ie.paths import require_ie_root

        root = require_ie_root()

    session = bind_local_session(
        root,
        space_id=args.space_id,
        identity_id=args.identity_id,
        handle=args.handle,
    )
    return serve_stdio(session)


if __name__ == "__main__":
    raise SystemExit(main())
