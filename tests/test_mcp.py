"""Unit tests for Identity-scoped local MCP Surface binding."""

from __future__ import annotations

import asyncio
import importlib.util
import tempfile
import unittest
from pathlib import Path

from ie.init_cmd import install_standard_skills
from runtime.database import Database, database_path, initialize_database
from runtime.mcp_handler import McpSurface, handle_rpc, TOOL_DEFS
from runtime.mcp_server import MCPBindingError, MCPIdentityBinding, create_mcp_server
from runtime.mcp_session import bind_local_session
from runtime.messaging import register_card, send_envelope
from runtime.models import ApplyStatus
from runtime.space_bootstrap import create_additional_identity

MCP_AVAILABLE = importlib.util.find_spec("mcp") is not None


def _structured(result):
    value = getattr(result, "structuredContent", None)
    if value is None:
        value = getattr(result, "structured_content", None)
    if value is None:
        raise AssertionError(f"MCP result has no structured content: {result!r}")
    return value


EXPECTED_TOOLS = {
    "ie_status",
    "ie_card",
    "ie_mass",
    "ie_freedom",
    "ie_signal_apply",
    "ie_geometry_feed",
    "ie_grants_list",
    "ie_requests_list",
    "ie_registry_list",
    "ie_identity_list",
    "ie_context_list",
    "ie_context_get",
    "ie_messaging_cards",
    "ie_messaging_status",
    "ie_messaging_card",
    "ie_messaging_card_register",
    "ie_messaging_inbox",
    "ie_messaging_send",
    "ie_messaging_metabolize",
}

MESSAGING_PEER_ID = "018f3a2b-7c9e-7d01-8a2b-0000000000aa"


def _messaging_card(identity_id: str, name: str) -> dict:
    return {
        "identityId": identity_id,
        "name": name,
        "type": "agent",
        "version": "0.1",
        "endpoints": {"messaging": "http://127.0.0.1:7420/messaging"},
        "recognitionPolicy": {"default": "accept-all"},
    }


def _add_second_identity(install: Path, handle: str = "other") -> str:
    with Database(database_path(install)) as database:
        with database.transaction() as conn:
            install_row = conn.execute("SELECT install_id FROM install LIMIT 1").fetchone()
            result = create_additional_identity(
                conn,
                install_id=install_row["install_id"],
                handle=handle,
                preferred_name=handle.title(),
                substrate="human",
            )
    return str(result["identity_id"])


class McpSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.install = Path(self._tmp.name) / "install"
        meta = initialize_database(
            self.install, handle="me", preferred_name="Me"
        )
        self.identity_id = meta["identity_id"]

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_bind_local_session(self) -> None:
        session = bind_local_session(self.install)
        self.assertEqual(session.identity_id, self.identity_id)
        self.assertEqual(session.local_handle, "me")
        self.assertEqual(session.preferred_name, "Me")
        env = session.actor_envelope()
        self.assertEqual(env["actor_identity_id"], self.identity_id)
        self.assertEqual(env["local_handle"], "me")
        if session.space_id is not None:
            self.assertEqual(env.get("space_id"), session.space_id)
            self.assertTrue(isinstance(session.space_id, str))

    def test_bind_by_identity_id(self) -> None:
        other_id = _add_second_identity(self.install, handle="other")
        session = bind_local_session(self.install, identity_id=other_id)
        self.assertEqual(session.identity_id, other_id)
        self.assertEqual(session.local_handle, "other")
        active = bind_local_session(self.install)
        self.assertEqual(active.identity_id, self.identity_id)

    def test_bind_by_handle(self) -> None:
        other_id = _add_second_identity(self.install, handle="agent")
        session = bind_local_session(self.install, handle="agent")
        self.assertEqual(session.identity_id, other_id)
        self.assertEqual(session.local_handle, "agent")

    def test_bind_rejects_unknown_handle(self) -> None:
        with self.assertRaises(RuntimeError):
            bind_local_session(self.install, handle="does-not-exist")

    def test_bind_rejects_both_selectors(self) -> None:
        with self.assertRaises(ValueError):
            bind_local_session(
                self.install, identity_id=self.identity_id, handle="me"
            )

    def test_bind_rejects_missing_db(self) -> None:
        with self.assertRaises(FileNotFoundError):
            bind_local_session(self.install / "does-not-exist")

    def test_with_actor_stamps_envelope(self) -> None:
        session = bind_local_session(self.install)
        payload = session.with_actor({"ok": True})
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["actor"]["actor_identity_id"], self.identity_id)


class McpToolTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.install = Path(self._tmp.name) / "install"
        meta = initialize_database(
            self.install, handle="me", preferred_name="Me"
        )
        self.identity_id = meta["identity_id"]
        install_standard_skills(self.install)
        self.session = bind_local_session(self.install)
        self.surface = McpSurface(self.session)
        register_card(self.install, _messaging_card(self.identity_id, "Me"))
        register_card(self.install, _messaging_card(MESSAGING_PEER_ID, "Peer"))

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_tools_list_has_expected_names(self) -> None:
        names = {t["name"] for t in TOOL_DEFS}
        self.assertEqual(names, EXPECTED_TOOLS)

    def test_status_includes_actor(self) -> None:
        result = self.surface.call_tool("ie_status", {})
        self.assertIn("actor", result)
        self.assertEqual(result["actor"]["actor_identity_id"], self.identity_id)
        self.assertEqual(result["identity_id"], self.identity_id)

    def test_card_includes_actor(self) -> None:
        result = self.surface.call_tool("ie_card", {})
        self.assertIn("actor", result)
        self.assertEqual(result["actor"]["actor_identity_id"], self.identity_id)

    def test_mass_includes_actor(self) -> None:
        result = self.surface.call_tool("ie_mass", {})
        self.assertIn("actor", result)
        self.assertEqual(result["actor"]["actor_identity_id"], self.identity_id)

    def test_freedom_includes_actor(self) -> None:
        result = self.surface.call_tool("ie_freedom", {})
        self.assertIn("actor", result)
        self.assertEqual(result["actor"]["actor_identity_id"], self.identity_id)
        self.assertIn("effective_freedom", result)
        self.assertNotIn("sources", result)
        detailed = self.surface.call_tool("ie_freedom", {"detail": True})
        self.assertIn("sources", detailed)

    def test_geometry_feed_includes_actor(self) -> None:
        result = self.surface.call_tool("ie_geometry_feed", {"limit": 5})
        self.assertIn("actor", result)
        self.assertEqual(result["actor"]["actor_identity_id"], self.identity_id)

    def test_grants_list_includes_actor(self) -> None:
        result = self.surface.call_tool("ie_grants_list", {})
        self.assertIn("actor", result)
        self.assertIn("grants", result)
        self.assertIsInstance(result["grants"], list)

    def test_requests_list_includes_actor(self) -> None:
        result = self.surface.call_tool("ie_requests_list", {})
        self.assertIn("actor", result)
        self.assertIn("requests", result)
        self.assertIsInstance(result["requests"], list)

    def test_requests_list_rejects_bad_status(self) -> None:
        with self.assertRaises(ValueError):
            self.surface.call_tool("ie_requests_list", {"status": "nope"})

    def test_registry_list_includes_actor(self) -> None:
        result = self.surface.call_tool("ie_registry_list", {})
        self.assertIn("actor", result)
        self.assertIn("peers", result)

    def test_identity_list_marks_session_bound(self) -> None:
        other_id = _add_second_identity(self.install, handle="other")
        session = bind_local_session(self.install, identity_id=other_id)
        surface = McpSurface(session)
        result = surface.call_tool("ie_identity_list", {})
        identities = result["identities"]
        bound = [i for i in identities if i.get("session_bound")]
        self.assertEqual(len(bound), 1)
        self.assertEqual(bound[0]["identity_id"], other_id)

    def test_context_list_and_get_are_identity_scoped(self) -> None:
        result = self.surface.call_tool("ie_context_list", {})
        self.assertEqual(result["identity_id"], self.identity_id)
        self.assertIn("onboarding", {item["name"] for item in result["skills"]})

        document = self.surface.call_tool("ie_context_get", {"name": "onboarding"})
        self.assertEqual(document["actor"]["actor_identity_id"], self.identity_id)
        self.assertIn("Account != Identity", document["body"])
        with self.assertRaises(ValueError):
            self.surface.call_tool("ie_context_get", {"name": "../IE"})

    def test_messaging_card_register_forces_bound_identity(self) -> None:
        result = self.surface.call_tool(
            "ie_messaging_card_register",
            {"card": _messaging_card("foreign-identity", "Bound card")},
        )
        self.assertEqual(result["card"]["identityId"], self.identity_id)
        self.assertEqual(result["actor"]["actor_identity_id"], self.identity_id)

    def test_messaging_status_includes_actor_and_policy_readouts(self) -> None:
        result = self.surface.call_tool("ie_messaging_status", {})
        self.assertEqual(result["identity_id"], self.identity_id)
        self.assertEqual(result["actor"]["actor_identity_id"], self.identity_id)
        self.assertIn("receipts", result)
        self.assertIn("consent_audit", result)
        self.assertIn("damping", result)

    def test_messaging_send_forces_bound_sender(self) -> None:
        result = self.surface.call_tool(
            "ie_messaging_send",
            {
                "envelope": {
                    "from": "foreign-identity",
                    "to": MESSAGING_PEER_ID,
                    "signal": {"type": "task"},
                    "payload": {"contentType": "text/plain", "inline": "task"},
                }
            },
        )
        self.assertEqual(result["status"], "delivered")
        self.assertEqual(result["envelope"]["from"], self.identity_id)
        self.assertEqual(result["actor"]["actor_identity_id"], self.identity_id)

    def test_messaging_inbox_filters_to_bound_receiver(self) -> None:
        peer_to_me = send_envelope(
            self.install,
            {
                "from": MESSAGING_PEER_ID,
                "to": self.identity_id,
                "signal": {"type": "task"},
                "payload": {"contentType": "text/plain", "inline": "inbox"},
            },
        )
        self.assertEqual(peer_to_me.status, "delivered")
        peer_message = send_envelope(
            self.install,
            {
                "from": self.identity_id,
                "to": MESSAGING_PEER_ID,
                "signal": {"type": "task"},
                "payload": {"contentType": "text/plain", "inline": "other inbox"},
            },
        )
        self.assertEqual(peer_message.status, "delivered")

        result = self.surface.call_tool("ie_messaging_inbox", {})
        self.assertEqual(result["actor"]["actor_identity_id"], self.identity_id)
        self.assertEqual(
            [message["messageId"] for message in result["messages"]],
            [peer_to_me.envelope["messageId"]],
        )

    def test_messaging_metabolize_rejects_foreign_receiver(self) -> None:
        result = send_envelope(
            self.install,
            {
                "from": self.identity_id,
                "to": MESSAGING_PEER_ID,
                "signal": {"type": "task"},
                "payload": {"contentType": "text/plain", "inline": "private"},
            },
        )
        with self.assertRaises(ValueError):
            self.surface.call_tool(
                "ie_messaging_metabolize",
                {"message_id": result.envelope["messageId"]},
            )

    def test_messaging_metabolize_records_bound_receiver(self) -> None:
        result = send_envelope(
            self.install,
            {
                "from": MESSAGING_PEER_ID,
                "to": self.identity_id,
                "signal": {"type": "task"},
                "payload": {"contentType": "text/plain", "inline": "accepted"},
            },
        )
        metabolized = self.surface.call_tool(
            "ie_messaging_metabolize",
            {
                "message_id": result.envelope["messageId"],
                "classification": "task-accepted",
                "notes": "accepted through MCP",
            },
        )
        self.assertEqual(metabolized["status"], "metabolized")
        self.assertEqual(metabolized["record"]["to"], self.identity_id)
        self.assertEqual(metabolized["actor"]["actor_identity_id"], self.identity_id)

    def test_signal_apply_forces_to_bound_identity(self) -> None:
        signal = {
            "from": "peer-alice",
            "to": "someone-else",
            "timestamp": "2026-08-09T12:00:00+00:00",
            "existence": True,
            "interaction_depth_delta": 0.1,
        }
        result = self.surface.call_tool(
            "ie_signal_apply", {"signal": signal, "open_consent": True}
        )
        self.assertIn("actor", result)
        self.assertEqual(result["actor"]["actor_identity_id"], self.identity_id)
        self.assertIn(
            result.get("status"),
            {ApplyStatus.APPLIED.value, "applied", ApplyStatus.PARTIAL.value, "partial"},
            msg=f"unexpected receipt keys: {list(result.keys())}",
        )

    def test_unknown_tool_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.surface.call_tool("ie_does_not_exist", {})


class McpRpcTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.install = Path(self._tmp.name) / "install"
        meta = initialize_database(self.install, handle="me", preferred_name="Me")
        self.identity_id = meta["identity_id"]
        install_standard_skills(self.install)
        register_card(self.install, _messaging_card(self.identity_id, "Me"))
        register_card(self.install, _messaging_card(MESSAGING_PEER_ID, "Peer"))
        self.session = bind_local_session(self.install)
        self.surface = McpSurface(self.session)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _call_tool(self, request_id: int, name: str, arguments: dict) -> dict:
        response = handle_rpc(
            self.surface,
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            },
        )
        assert response is not None
        result = response["result"]
        self.assertFalse(result.get("isError"), result)
        return result["structuredContent"]

    def test_initialize(self) -> None:
        resp = handle_rpc(
            self.surface,
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        assert resp is not None
        self.assertEqual(resp["id"], 1)
        self.assertIn("result", resp)
        self.assertEqual(resp["result"]["serverInfo"]["name"], "ie-os-local")
        self.assertEqual(resp["result"]["serverInfo"]["version"], "1")

    def test_tools_list(self) -> None:
        resp = handle_rpc(
            self.surface,
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        assert resp is not None
        tools = resp["result"]["tools"]
        self.assertEqual(len(tools), len(EXPECTED_TOOLS))
        self.assertEqual({t["name"] for t in tools}, EXPECTED_TOOLS)

    def test_tools_call_status(self) -> None:
        resp = handle_rpc(
            self.surface,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "ie_status", "arguments": {}},
            },
        )
        assert resp is not None
        result = resp["result"]
        self.assertFalse(result.get("isError"))
        structured = result.get("structuredContent") or {}
        self.assertIn("actor", structured)

    def test_tools_call_freedom(self) -> None:
        resp = handle_rpc(
            self.surface,
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "ie_freedom", "arguments": {}},
            },
        )
        assert resp is not None
        self.assertFalse(resp["result"].get("isError"))
        structured = resp["result"].get("structuredContent") or {}
        self.assertIn("effective_freedom", structured)

    def test_messaging_rpc_forces_card_identity_and_sender(self) -> None:
        registered = self._call_tool(
            5,
            "ie_messaging_card_register",
            {"card": _messaging_card("foreign-identity", "Bound through RPC")},
        )
        self.assertEqual(registered["card"]["identityId"], self.identity_id)
        self.assertEqual(registered["actor"]["actor_identity_id"], self.identity_id)

        sent = self._call_tool(
            6,
            "ie_messaging_send",
            {
                "envelope": {
                    "from": "foreign-identity",
                    "to": MESSAGING_PEER_ID,
                    "signal": {"type": "task"},
                    "payload": {"contentType": "text/plain", "inline": "RPC task"},
                }
            },
        )
        self.assertEqual(sent["status"], "delivered")
        self.assertEqual(sent["envelope"]["from"], self.identity_id)
        self.assertEqual(sent["actor"]["actor_identity_id"], self.identity_id)

    def test_messaging_rpc_filters_inbox_and_rejects_foreign_metabolize(self) -> None:
        inbound = send_envelope(
            self.install,
            {
                "from": MESSAGING_PEER_ID,
                "to": self.identity_id,
                "signal": {"type": "task"},
                "payload": {"contentType": "text/plain", "inline": "inbound"},
            },
        )
        foreign_receiver = send_envelope(
            self.install,
            {
                "from": self.identity_id,
                "to": MESSAGING_PEER_ID,
                "signal": {"type": "task"},
                "payload": {"contentType": "text/plain", "inline": "peer-only"},
            },
        )

        inbox = self._call_tool(7, "ie_messaging_inbox", {})
        self.assertEqual(
            [message["messageId"] for message in inbox["messages"]],
            [inbound.envelope["messageId"]],
        )
        self.assertEqual(inbox["actor"]["actor_identity_id"], self.identity_id)

        rejected = handle_rpc(
            self.surface,
            {
                "jsonrpc": "2.0",
                "id": 8,
                "method": "tools/call",
                "params": {
                    "name": "ie_messaging_metabolize",
                    "arguments": {"message_id": foreign_receiver.envelope["messageId"]},
                },
            },
        )
        assert rejected is not None
        self.assertTrue(rejected["result"]["isError"])
        error = rejected["result"]["structuredContent"]
        self.assertEqual(error["actor"]["actor_identity_id"], self.identity_id)

        metabolized = self._call_tool(
            9,
            "ie_messaging_metabolize",
            {
                "message_id": inbound.envelope["messageId"],
                "classification": "task-accepted",
            },
        )
        self.assertEqual(metabolized["status"], "metabolized")
        self.assertEqual(metabolized["record"]["to"], self.identity_id)
        self.assertEqual(metabolized["actor"]["actor_identity_id"], self.identity_id)

    def test_notification_returns_none(self) -> None:
        resp = handle_rpc(
            self.surface,
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
        )
        self.assertIsNone(resp)


class MCPBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.install = Path(self._tmp.name) / "install"
        initialize_database(self.install, handle="me", preferred_name="Me")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_binding_is_canonical_and_space_context_fails_closed(self):
        binding = MCPIdentityBinding.from_install(self.install)
        self.assertEqual(binding.local_handle, "me")
        self.assertTrue(binding.identity_id)

        with self.assertRaisesRegex(MCPBindingError, "identity binding mismatch"):
            MCPIdentityBinding.from_install(self.install, identity_id="other")
        with self.assertRaisesRegex(MCPBindingError, "unenforced membrane context"):
            MCPIdentityBinding.from_install(self.install, space_id="space-1")

    @unittest.skipUnless(MCP_AVAILABLE, "install ie-os[mcp] to run protocol dispatch tests")
    def test_read_and_apply_dispatch_use_bound_identity(self):
        binding = MCPIdentityBinding.from_install(self.install)
        server = create_mcp_server(binding)
        tool_names = {tool.name for tool in asyncio.run(server.list_tools())}
        self.assertIn("get_public_card", tool_names)
        self.assertIn("receive_interaction_signal", tool_names)

        card_result = asyncio.run(server.call_tool("get_public_card", {}))
        card = _structured(card_result)
        self.assertEqual(card["actor_identity_id"], binding.identity_id)
        self.assertEqual(card["result"]["local_handle"], "me")

        apply_result = asyncio.run(
            server.call_tool(
                "receive_interaction_signal",
                {
                    "payload": {
                        "from": "alice",
                        "to": "me",
                        "timestamp": "2026-08-09T10:00:00+00:00",
                        "existence": True,
                        "interaction_depth_delta": 0.2,
                    }
                },
            )
        )
        receipt = _structured(apply_result)
        self.assertEqual(receipt["actor_identity_id"], binding.identity_id)
        self.assertEqual(receipt["result"]["status"], "applied")

        rejected_result = asyncio.run(
            server.call_tool(
                "receive_interaction_signal",
                {
                    "payload": {
                        "from": "alice",
                        "to": "someone-else",
                        "timestamp": "2026-08-09T10:01:00+00:00",
                        "existence": True,
                        "interaction_depth_delta": 0.2,
                    }
                },
            )
        )
        rejected = _structured(rejected_result)
        self.assertEqual(rejected["actor_identity_id"], binding.identity_id)
        self.assertEqual(rejected["result"]["status"], "rejected")


if __name__ == "__main__":
    unittest.main()
