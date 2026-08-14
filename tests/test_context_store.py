"""ContextStore local_fs + Notion (mocked) tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

from ie.init_cmd import init_install
from runtime.context_store import (
    ContextStoreError,
    LocalFsContextStore,
    open_context_store,
    write_adapter_config,
    adapter_status,
)
from runtime.notion_context_store import NotionClient, NotionContextStore


class LocalFsContextStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name) / "install"
        init_install(self.root, handle="me", preferred_name="Me")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_list_and_read_standard_skills(self) -> None:
        store = LocalFsContextStore(self.root)
        names = {r.name for r in store.list_skills()}
        self.assertIn("mature", names)
        doc = store.read_skill("mature")
        self.assertIn("ie mature", doc.body)
        self.assertEqual(doc.source, "local_fs")

    def test_open_defaults_to_local_fs(self) -> None:
        store = open_context_store(self.root)
        self.assertEqual(store.kind, "local_fs")

    def test_adapter_status(self) -> None:
        info = adapter_status(self.root)
        self.assertEqual(info["configured_adapter"], "local_fs")
        self.assertEqual(info["effective_adapter"], "local_fs")
        self.assertGreaterEqual(info["skill_count"], 1)

    def test_write_skill(self) -> None:
        store = LocalFsContextStore(self.root)
        store.write_skill("custom", "# Custom\n\nbody\n")
        doc = store.read_skill("custom")
        self.assertEqual(doc.body, "# Custom\n\nbody\n")


class NotionContextStoreTests(unittest.TestCase):
    def test_list_and_read_with_mock_client(self) -> None:
        client = MagicMock(spec=NotionClient)

        def page_title(page: dict[str, Any]) -> str:
            if page.get("type") == "child_page":
                return str((page.get("child_page") or {}).get("title") or "")
            return ""

        client.page_title.side_effect = page_title

        def list_children(page_id: str) -> list[dict[str, Any]]:
            if page_id == "root":
                return [
                    {
                        "id": "skills-parent",
                        "type": "child_page",
                        "child_page": {"title": "Skills"},
                    }
                ]
            if page_id == "skills-parent":
                return [
                    {
                        "id": "skill-mature",
                        "type": "child_page",
                        "child_page": {"title": "mature"},
                    }
                ]
            if page_id == "skill-mature":
                return [
                    {
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"plain_text": "Run ie mature via CLI."}]
                        },
                    }
                ]
            return []

        client.list_children.side_effect = list_children

        store = NotionContextStore(
            install_root=Path("/tmp/unused"),
            client=client,
            root_page_id="root",
        )
        refs = store.list_skills()
        self.assertEqual([r.name for r in refs], ["mature"])
        doc = store.read_skill("mature")
        self.assertIn("ie mature", doc.body)
        self.assertEqual(doc.source, "notion")

    def test_missing_token_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".ie").mkdir()
            write_adapter_config(
                root, {"adapter": "notion", "root_page_id": "abc"}
            )
            with self.assertRaises(ContextStoreError):
                open_context_store(root)


if __name__ == "__main__":
    unittest.main()
