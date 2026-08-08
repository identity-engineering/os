"""Tests for local IE install root discovery."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from ie.cli import _resolve_source_refs, app
from ie.paths import find_ie_root


class PathDiscoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.config_home = base / "config"
        self.install = base / "install"
        self.workdir = base / "elsewhere"
        self.workdir.mkdir()

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_init_remembers_root_for_commands_from_elsewhere(self):
        env = {"XDG_CONFIG_HOME": str(self.config_home), "IE_ROOT": ""}
        with patch.dict(os.environ, env):
            result = CliRunner().invoke(
                app,
                [
                    "init",
                    "--path",
                    str(self.install),
                    "--account",
                    "no_account",
                    "--name",
                    "First User",
                    "--handle",
                    "first-user",
                    "--yes",
                ],
            )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertTrue((self.install / ".ie" / "ie.sqlite3").is_file())
            self.assertTrue((self.install / "README.md").is_file())
            self.assertTrue((self.install / "IE.md").is_file())
            self.assertFalse((self.install / "HEADER.yaml").exists())
            self.assertFalse((self.install / "registry").exists())
            self.assertEqual(find_ie_root(self.workdir), self.install.resolve())
            self.assertEqual(
                (self.config_home / "ie-os" / "active-root").read_text(
                    encoding="utf-8"
                ).strip(),
                str(self.install.resolve()),
            )

    def test_default_home_root_is_discovered_without_registration(self):
        default_root = Path(self._tmp.name) / "ie"
        (default_root / ".ie").mkdir(parents=True)
        (default_root / ".ie" / "ie.sqlite3").touch()

        env = {"XDG_CONFIG_HOME": str(self.config_home), "IE_ROOT": ""}
        with patch.dict(os.environ, env), patch("ie.paths.Path.home", return_value=Path(self._tmp.name)):
            self.assertEqual(find_ie_root(self.workdir), default_root.resolve())

    def test_mature_sources_are_existing_root_relative_files(self):
        trajectory = self.install / "trajectory"
        trajectory.mkdir(parents=True)
        source = trajectory / "2026-08-05.yaml"
        source.write_text("state: changed\n", encoding="utf-8")

        self.assertEqual(
            _resolve_source_refs(
                self.install,
                ["trajectory/2026-08-05.yaml", str(source)],
            ),
            ["trajectory/2026-08-05.yaml"],
        )

        with self.assertRaisesRegex(SystemExit, "inside the install root"):
            _resolve_source_refs(self.install, [str(self._tmp.name)])


if __name__ == "__main__":
    unittest.main()