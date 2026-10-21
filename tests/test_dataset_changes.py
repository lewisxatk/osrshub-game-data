"""Tests for ID-based dataset change reports."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import report_dataset_changes as changes


class DatasetChangeTests(unittest.TestCase):
    def test_reports_added_removed_and_changed_records(self):
        before = {"1": {"id": 1, "name": "Bronze sword", "weight": 1},
                  "2": {"id": 2, "name": "Old item"}}
        after = {"1": {"id": 1, "name": "Bronze sword", "weight": 0.9},
                 "3": {"id": 3, "name": "New item"}}
        result = changes.compare_records(before, after)
        self.assertEqual(result["added_count"], 1)
        self.assertEqual(result["removed_count"], 1)
        self.assertEqual(result["changed_record_count"], 1)
        self.assertEqual(result["changed_records"][0]["fields"], ["weight"])
        self.assertEqual(result["changed_field_counts"], {"weight": 1})

    def test_zero_and_false_values_are_compared_not_dropped(self):
        result = changes.compare_records(
            {"1": {"id": 1, "value": 1, "enabled": True}},
            {"1": {"id": 1, "value": 0, "enabled": False}},
        )
        self.assertEqual(result["changed_records"][0]["fields"], ["enabled", "value"])

    def test_duplicate_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "duplicate.json"
            path.write_text('[{"id":1},{"id":1}]', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate id"):
                changes.load_records(path)

    def test_non_array_dataset_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "object.json"
            path.write_text('{"id":1}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "JSON array"):
                changes.load_records(path)


if __name__ == "__main__":
    unittest.main()
