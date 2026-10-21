"""Unit tests for dataset normalization and conflict reporting."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_dataset


class PipelineTests(unittest.TestCase):
    def test_numeric_id_variants(self):
        self.assertEqual(build_dataset.numeric_id({"id": "4151"}), 4151)
        self.assertEqual(build_dataset.numeric_id({"item_id": 11802}), 11802)
        self.assertIsNone(build_dataset.numeric_id({"id": "not-an-id"}))

    def test_name_variants(self):
        self.assertEqual(build_dataset.name_of({"name": "Whip"}), "Whip")
        self.assertEqual(build_dataset.name_of({"item_name": "Rune platebody"}), "Rune platebody")
        self.assertEqual(build_dataset.name_of({}), "")

    def test_volatile_conflict_fields_are_ignored(self):
        self.assertTrue(build_dataset._is_ignored_conflict_field("last_updated"))
        self.assertTrue(build_dataset._is_ignored_conflict_field("icon_large"))
        self.assertFalse(build_dataset._is_ignored_conflict_field("attack_speed"))

    def test_large_conflict_values_are_summarized(self):
        summary = build_dataset._value_summary("x" * 1000)
        self.assertIsInstance(summary, dict)
        self.assertTrue(summary["truncated"])
        self.assertEqual(summary["characters"], 1002)

    def test_merge_keeps_source_attribution_without_raw_record_duplication(self):
        with tempfile.TemporaryDirectory() as directory:
            raw = Path(directory)
            (raw / "community_items.json").write_text(json.dumps([{
                "id": 4151, "name": "Abyssal whip", "attack_speed": 4,
                "last_updated": "2025-01-01", "icon": "first",
            }]), encoding="utf-8")
            (raw / "original_items.json").write_text(json.dumps([{
                "id": 4151, "name": "Abyssal whip", "attack_speed": 5,
                "last_updated": "2026-01-01", "icon": "second",
            }]), encoding="utf-8")
            with patch.object(build_dataset, "RAW", raw):
                records, conflicts, missing, ignored = build_dataset.merge_category("items")
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["sources"], ["community_items", "original_items"])
            self.assertNotIn("source_records", records[0])
            self.assertEqual(len(conflicts), 1)
            self.assertEqual(conflicts[0]["field"], "attack_speed")
            self.assertEqual(missing, [])
            self.assertEqual(ignored, {"icon": 1, "last_updated": 1})


if __name__ == "__main__":
    unittest.main()
