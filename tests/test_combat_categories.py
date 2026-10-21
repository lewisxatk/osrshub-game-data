"""Tests for normalized combat category coverage."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from report_combat_categories import summarize


class CombatCategoryTests(unittest.TestCase):
    def test_counts_categories_and_missing_values(self):
        result = summarize([
            {"id": 1, "slot": "Head"},
            {"id": 2, "slot": "head "},
            {"id": 3, "slot": None},
        ], "slot")
        self.assertEqual(result["category_counts"], {"head": 2})
        self.assertEqual(result["missing_category_count"], 1)

    def test_flags_invalid_records_and_duplicate_ids(self):
        result = summarize([{"id": 1, "slot": "weapon"}, {"id": 1, "slot": "shield"}, None], "slot")
        self.assertEqual(result["duplicate_ids"], [1])
        self.assertEqual(result["invalid_record_count"], 1)

    def test_rejects_non_array(self):
        with self.assertRaisesRegex(ValueError, "JSON array"):
            summarize({}, "slot")


if __name__ == "__main__":
    unittest.main()
