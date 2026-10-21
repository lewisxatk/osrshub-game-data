"""Tests for the item identity/collision audit."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from report_item_identity import audit_items, normalize_name


class ItemIdentityTests(unittest.TestCase):
    def test_normalizes_punctuation_and_spacing_for_review_only(self):
        self.assertEqual(normalize_name("  Dragon   scimitar! "), "dragon scimitar")

    def test_reports_exact_name_collisions_without_merging_ids(self):
        result = audit_items([
            {"id": 1, "name": "Dragon scimitar", "sources": ["source_a"]},
            {"id": 2, "name": "Dragon scimitar", "sources": ["source_b"]},
        ])
        self.assertEqual(result["exact_name_collision_group_count"], 1)
        self.assertEqual(result["item_record_count"], 2)
        self.assertEqual(result["valid_unique_id_count"], 2)
        self.assertEqual(result["status"], "passed")

    def test_reports_punctuation_case_collision_separately(self):
        result = audit_items([
            {"id": 1, "name": "Dragon scimitar"},
            {"id": 2, "name": "dragon-scimitar"},
        ])
        self.assertEqual(result["exact_name_collision_group_count"], 0)
        self.assertEqual(result["normalized_name_collision_group_count"], 1)

    def test_duplicate_ids_fail_structural_audit(self):
        result = audit_items([
            {"id": 1, "name": "One"},
            {"id": 1, "name": "Different name"},
        ])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["duplicate_ids"], [1])

    def test_missing_names_are_reported_not_invented(self):
        result = audit_items([{"id": 7}, {"id": 8, "name": "  "}])
        self.assertEqual(result["missing_name_count"], 2)
        self.assertEqual(result["status"], "passed")

    def test_rejects_non_array_dataset(self):
        with self.assertRaisesRegex(ValueError, "JSON array"):
            audit_items({"one": {"id": 1, "name": "One"}})


if __name__ == "__main__":
    unittest.main()
