"""Tests for the local install status summary."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ie.status_cmd import collect_status


class StatusTests(unittest.TestCase):
    def test_status_ignores_foreign_estimate_documentation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            foreign = root / "registry" / "_foreign_estimates"
            foreign.mkdir(parents=True)
            (foreign / "README.md").write_text("documentation\n", encoding="utf-8")
            (foreign / "_example.yaml").write_text("{}\n", encoding="utf-8")
            (foreign / "alice.yaml").write_text("sender_handle: alice\n", encoding="utf-8")

            status = collect_status(root)

            self.assertEqual(status["foreign_estimate_senders"], ["alice"])


if __name__ == "__main__":
    unittest.main()