"""Tests for source conflict prioritization."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import report_conflict_priorities as priorities


class ConflictPriorityTests(unittest.TestCase):
    def test_priority_classifies_combat_fields(self):
        self.assertEqual(priorities.priority_for_field("attack_speed"), "high")
        self.assertEqual(priorities.priority_for_field("examine"), "review")

    def test_conflicts_are_grouped_by_field_and_category(self):
        rows = [
            {"category": "items", "id": 1, "name": "Test sword", "field": "weapon",
             "kept_source": "a", "other_source": "b"},
            {"category": "items", "id": 2, "name": "Test bow", "field": "weapon",
             "kept_source": "a", "other_source": "b"},
            {"category": "monsters", "id": 3, "name": "Test NPC", "field": "combat_level"},
        ]
        report = priorities.summarize_conflicts(rows)
        self.assertEqual(report["conflict_count"], 3)
        self.assertEqual(report["fields_ranked_by_conflict_count"][0]["field"], "weapon")
        self.assertEqual(report["fields_ranked_by_conflict_count"][0]["conflict_count"], 2)

    def test_malformed_conflicts_are_counted(self):
        report = priorities.summarize_conflicts([None, {"category": "items"}])
        self.assertEqual(report["invalid_record_count"], 2)

    def test_json_object_wrapper_supported(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "conflicts.json"
            p.write_text(json.dumps({"conflicts": [{"field": "max_hit"}]}), encoding="utf-8")
            self.assertEqual(priorities.load_conflicts(p)[0]["field"], "max_hit")


if __name__ == "__main__":
    unittest.main()
