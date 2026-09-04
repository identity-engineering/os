"""Validate the deterministic Messaging v0.1 fixtures."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).parents[1]
SCHEMA_ROOT = ROOT / "schemas" / "messaging" / "v0.1"
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "messaging" / "v0.1"


class MessagingSchemaTests(unittest.TestCase):
    def _load(self, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))

    def test_schemas_are_valid_and_fixtures_match(self) -> None:
        cases = (
            ("identity-card.json", sorted(FIXTURE_ROOT.glob("card-*.json"))),
            ("message-envelope.json", sorted(FIXTURE_ROOT.glob("envelope-*.json"))),
        )
        for schema_name, fixture_paths in cases:
            schema = self._load(SCHEMA_ROOT / schema_name)
            Draft202012Validator.check_schema(schema)
            validator = Draft202012Validator(schema, format_checker=FormatChecker())
            self.assertTrue(fixture_paths, f"no fixtures found for {schema_name}")
            for fixture_path in fixture_paths:
                errors = sorted(
                    validator.iter_errors(self._load(fixture_path)),
                    key=lambda error: list(error.path),
                )
                self.assertEqual(
                    errors,
                    [],
                    f"{fixture_path.relative_to(ROOT)} does not match {schema_name}",
                )


if __name__ == "__main__":
    unittest.main()