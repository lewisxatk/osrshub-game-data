"""Tests for normalized item skill requirements."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_item_requirements import normalize_requirements


class ItemRequirementTests(unittest.TestCase):
    def test_normalizes_skill_requirements_and_preserves_provenance(self):
        rows, report = normalize_requirements([{
            "id": 4151, "name": "Abyssal whip", "sources": ["community_items"],
            "wiki_url": "https://oldschool.runescape.wiki/w/Abyssal_whip",
            "equipment": {"requirements": {"Attack": 70, " Slayer ": 0}},
        }])
        self.assertEqual(rows[0]["requirements"], [
            {"skill": "Attack", "level": 70}, {"skill": "Slayer", "level": 0}
        ])
        self.assertEqual(rows[0]["sources"], ["community_items"])
        self.assertEqual(report["items_with_skill_requirements"], 1)

    def test_invalid_levels_are_reported_not_guessed(self):
        rows, report = normalize_requirements([{
            "id": 1, "name": "Example", "equipment": {
                "requirements": {"Attack": "70", "Magic": -1, "Defence": True}
            }
        }])
        self.assertEqual(rows, [])
        self.assertEqual(report["warning_count"], 3)

    def test_items_without_requirements_are_not_emitted(self):
        rows, report = normalize_requirements([{"id": 1, "name": "No requirements"}])
        self.assertEqual(rows, [])
        self.assertEqual(report["requirement_entry_count"], 0)

    def test_duplicate_item_ids_fail(self):
        with self.assertRaisesRegex(ValueError, "duplicate item ID"):
            normalize_requirements([{"id": 1}, {"id": 1}])

    def test_non_array_fails(self):
        with self.assertRaisesRegex(ValueError, "JSON array"):
            normalize_requirements({})


if __name__ == "__main__":
    unittest.main()
