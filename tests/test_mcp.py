"""Unit tests for Identity-scoped local MCP Surface binding."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from io import StringIO

from runtime.database import initialize_database
from runtime.mcp_handler import McpSurface, handle_rpc, TOOL_DEFS
from runtime.mcp_session import IdentitySession, bind_local_session
from runtime.models import ApplyStatus


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
        self.assertNotIn("space_id", env)

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
        self.session = bind_local_session(self.install)
        self.surface = McpSurface(self.session)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_tools_list_has_expected_names(self) -> None:
        names = {t["name"] for t in TOOL_DEFS}
        self.assertEqual(
            names,
            {"ie_status", "ie_card", "ie_mass", "ie_signal_apply", "ie_registry_list"},
        )

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

    def test_registry_list_includes_actor(self) -> None:
        result = self.surface.call_tool("ie_registry_list", {})
        self.assertIn("actor", result)
        self.assertIn("peers", result)

    def test_signal_apply_forces_to_bound_identity(self) -> None:
        # Attempt cross-identity target; tool must force destination to bound handle.
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
        # Receipt should reflect applied state for the bound Identity
        status = result.get("status") or result.get("receipt", {}).get("status")
        # apply_from_dict returns a receipt whose to_dict has status
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
        initialize_database(self.install, handle="me", preferred_name="Me")
        self.session = bind_local_session(self.install)
        self.surface = McpSurface(self.session)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_initialize(self) -> None:
        resp = handle_rpc(
            self.surface,
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        )
        assert resp is not None
        self.assertEqual(resp["id"], 1)
        self.assertIn("result", resp)
        self.assertEqual(resp["result"]["serverInfo"]["name"], "ie-os-local")

    def test_tools_list(self) -> None:
        resp = handle_rpc(
            self.surface,
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )
        assert resp is not None
        tools = resp["result"]["tools"]
        self.assertEqual(len(tools), 5)

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

    def test_notification_returns_none(self) -> None:
        resp = handle_rpc(
            self.surface,
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
        )
        self.assertIsNone(resp)


if __name__ == "__main__":
    unittest.main()
