"""Context Layer standard skills on ie init."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ie.init_cmd import init_install, install_standard_skills
from ie.paths import STANDARD_SKILL_NAMES, bundled_skills_dir


class SkillsInitTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.install = Path(self._tmp.name) / "install"

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_bundled_skills_exist(self) -> None:
        root = bundled_skills_dir()
        for name in STANDARD_SKILL_NAMES:
            path = root / name / "SKILL.md"
            self.assertTrue(path.is_file(), f"missing template {path}")
            text = path.read_text(encoding="utf-8")
            self.assertIn("name:", text)
            self.assertNotIn("edit the database directly", text.lower())

    def test_init_installs_skills(self) -> None:
        init_install(self.install, handle="me", preferred_name="Me")
        for name in STANDARD_SKILL_NAMES:
            skill = self.install / "skills" / name / "SKILL.md"
            self.assertTrue(skill.is_file(), f"skill not installed: {skill}")
        ie_md = (self.install / "IE.md").read_text(encoding="utf-8")
        self.assertIn("skills/mature/SKILL.md", ie_md)
        self.assertIn("CLI", ie_md)

    def test_install_skills_idempotent_without_force(self) -> None:
        init_install(self.install, handle="me", preferred_name="Me")
        path = self.install / "skills" / "mature" / "SKILL.md"
        path.write_text("# local override\n", encoding="utf-8")
        install_standard_skills(self.install, force=False)
        self.assertEqual(path.read_text(encoding="utf-8"), "# local override\n")
        install_standard_skills(self.install, force=True)
        self.assertIn("Mature", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
