"""Regression tests for known-empty versus unknown item requirements."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_item_requirements import normalize_requirements


class ItemRequirementKnowledgeTests(unittest.TestCase):
    def test_explicit_empty_requirements_are_preserved_as_known_empty(self):
        rows, report = normalize_requirements([
            {"id": 1, "name": "No-requirement item", "equipment": {"slot": "weapon", "requirements": {}}}
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["requirements"], [])
        self.assertEqual(rows[0]["requirements_status"], "known_empty")
        self.assertEqual(report["items_with_explicit_empty_requirements"], 1)
        self.assertEqual(report["items_with_unknown_requirements"], 0)

    def test_missing_requirement_field_stays_unknown_and_is_not_emitted_as_empty(self):
        rows, report = normalize_requirements([
            {"id": 2, "name": "Unknown item", "equipment": {"slot": "weapon"}}
        ])
        self.assertEqual(rows, [])
        self.assertEqual(report["items_with_unknown_requirements"], 1)
        self.assertEqual(report["items_with_explicit_empty_requirements"], 0)

    def test_nonempty_requirements_are_normalized(self):
        rows, report = normalize_requirements([
            {"id": 3, "name": "Example", "equipment": {"requirements": {"attack": 70}}}
        ])
        self.assertEqual(rows[0]["requirements"], [{"skill": "attack", "level": 70}])
        self.assertEqual(rows[0]["requirements_status"], "known")
        self.assertEqual(report["items_with_nonempty_skill_requirements"], 1)

    def test_invalid_entries_mark_record_partial_instead_of_known_empty(self):
        rows, report = normalize_requirements([
            {"id": 4, "name": "Partial", "equipment": {"requirements": {"attack": "unknown"}}}
        ])
        self.assertEqual(rows[0]["requirements"], [])
        self.assertEqual(rows[0]["requirements_status"], "partial")
        self.assertEqual(report["items_with_partially_invalid_requirements"], 1)
        self.assertGreater(report["warning_count"], 0)


if __name__ == "__main__":
    unittest.main()
