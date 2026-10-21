"""Tests for source-backed combat reference regression checks."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_combat_reference as reference


class CombatReferenceTests(unittest.TestCase):
    def test_nested_fields_match_fixture(self):
        fixture = {"version": 1, "cases": [{
            "dataset": "equipment-stats.json", "id": 4151,
            "expected": {"name": "Abyssal whip", "bonuses.attack_slash": 82},
            "source": {"url": "https://example.com/item", "checked_on": "2026-01-01"}
        }]}
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "equipment-stats.json").write_text(json.dumps([
                {"id": 4151, "name": "Abyssal whip", "bonuses": {"attack_slash": 82}}
            ]), encoding="utf-8")
            result = reference.run_cases(fixture, Path(tmp))
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["passed_count"], 1)

    def test_mismatched_values_fail_with_actual_value(self):
        fixture = {"version": 1, "cases": [{
            "dataset": "weapons.json", "id": 1, "expected": {"attack_speed": 4},
            "source": {"url": "https://example.com/item", "checked_on": "2026-01-01"}
        }]}
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "weapons.json").write_text('[{"id":1,"attack_speed":5}]', encoding="utf-8")
            result = reference.run_cases(fixture, Path(tmp))
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failures"][0]["mismatches"]["attack_speed"]["actual"], 5)

    def test_invalid_fixture_is_rejected(self):
        self.assertTrue(reference.validate_fixture({"version": 2, "cases": []}))

    def test_missing_record_fails(self):
        fixture = {"version": 1, "cases": [{
            "dataset": "weapons.json", "id": 123, "expected": {"attack_speed": 4},
            "source": {"url": "https://example.com/item", "checked_on": "2026-01-01"}
        }]}
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "weapons.json").write_text("[]", encoding="utf-8")
            result = reference.run_cases(fixture, Path(tmp))
        self.assertEqual(result["failed_count"], 1)
        self.assertEqual(result["status"], "failed")


if __name__ == "__main__":
    unittest.main()
