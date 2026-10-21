"""Tests for database coverage scorecard semantics."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from report_database_scorecard import coverage, build_scorecard

class DatabaseScorecardTests(unittest.TestCase):
    def test_null_and_empty_are_missing_but_zero_is_present(self):
        rows = [{"id": 0, "name": "", "source_urls": None}, {"id": 1, "name": "Rune", "source_urls": []}]
        result = coverage(rows, ("id", "name", "source_urls"))
        self.assertEqual(result["fields"]["id"]["coverage_percent"], 100.0)
        self.assertEqual(result["fields"]["name"]["coverage_percent"], 50.0)
        self.assertEqual(result["fields"]["source_urls"]["coverage_percent"], 0.0)
        self.assertEqual(result["field_coverage_percent"], 50.0)

    def test_empty_dataset_is_zero_not_complete(self):
        result = coverage([], ("id", "name"))
        self.assertEqual(result["record_count"], 0)
        self.assertEqual(result["field_coverage_percent"], 0.0)

    def test_scorecard_reports_errors_for_missing_dataset(self):
        def loader(filename):
            if filename == "quests.json":
                raise ValueError("fixture missing")
            return [{"id": 1, "name": "fixture"}]
        report = build_scorecard(loader)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("fixture missing" in error for error in report["errors"]))

    def test_scorecard_labels_index_as_not_accuracy(self):
        def loader(filename):
            if filename == "item-combat-profiles.json":
                return [{"equipment_record_present": True, "source_urls": ["https://example.test"], "weapon_record_present": True, "attack_speed": 4}]
            return [{"id": 1, "name": "fixture", "members": False, "tradeable": True, "stackable": False, "slot": "weapon", "bonuses": {"slash": 1}, "requirements": [], "source_url": "https://example.test", "attack_speed": 4, "weapon_type": "test", "stances": [], "combat_level": 1, "hitpoints": 1, "attack_level": 1, "strength_level": 1, "defence_level": 1, "source_urls": ["https://example.test"], "quest_id": 1, "prerequisite_quest_ids": []}]
        report = build_scorecard(loader)
        self.assertIn("not overall OSRS database completeness", report["coverage_index_definition"])
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["datasets"]["item_combat_profiles"]["equipment_link_and_source_percent"], 100.0)
        self.assertIn("requirement_applicability", report["datasets"])

if __name__ == "__main__":
    unittest.main()
