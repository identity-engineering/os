"""Unit tests for Identity-scoped local MCP Surface binding."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from runtime.database import Database, database_path, initialize_database
from runtime.mcp_handler import McpSurface, handle_rpc, TOOL_DEFS
from runtime.mcp_session import bind_local_session
from runtime.models import ApplyStatus
from runtime.space_bootstrap import create_additional_identity

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
        # install active remains the first Identity
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
        self.session = bind_local_session(self.install)
        self.surface = McpSurface(self.session)

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

    def test_notification_returns_none(self) -> None:
        resp = handle_rpc(
            self.surface,
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
        )
        self.assertIsNone(resp)


if __name__ == "__main__":
    unittest.main()
