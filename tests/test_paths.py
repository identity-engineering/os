"""Tests for local IE install root discovery."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from ie.cli import app
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
                    "Jonas",
                    "--handle",
                    "jonas",
                    "--yes",
                ],
            )

            self.assertEqual(result.exit_code, 0, result.output)
            self.assertEqual(find_ie_root(self.workdir), self.install.resolve())
            self.assertEqual(
                (self.config_home / "ie-os" / "active-root").read_text(
                    encoding="utf-8"
                ).strip(),
                str(self.install.resolve()),
            )

    def test_default_home_root_is_discovered_without_registration(self):
        default_root = Path(self._tmp.name) / "ie"
        default_root.mkdir()
        (default_root / "HEADER.yaml").write_text("identity: {}\n", encoding="utf-8")

        env = {"XDG_CONFIG_HOME": str(self.config_home), "IE_ROOT": ""}
        with patch.dict(os.environ, env), patch("ie.paths.Path.home", return_value=Path(self._tmp.name)):
            self.assertEqual(find_ie_root(self.workdir), default_root.resolve())


if __name__ == "__main__":
    unittest.main()