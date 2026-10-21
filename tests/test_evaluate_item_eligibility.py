"""Tests for conservative profile-to-item eligibility evaluation."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import evaluate_item_eligibility as eligibility


class ItemEligibilityTests(unittest.TestCase):
    def setUp(self):
        self.items = [
            {"id": 10, "name": "Rune platebody"},
            {"id": 11, "name": "Dragon scimitar"},
            {"id": 12, "name": "Mystery item"},
            {"id": 13, "name": "Excluded by name"},
        ]
        self.requirements = [
            {"item_id": 10, "requirements": [{"skill": "Defence", "level": 40}], "sources": ["OSRS Wiki"], "source_url": "https://oldschool.runescape.wiki/w/Rune_platebody"},
            {"item_id": 11, "requirements": [{"skill": "Attack", "level": 60}], "sources": ["OSRSBox"]},
        ]
        self.profile = {"skills": {"defence": 50, "Attack": 55}, "completed_quests": ["Monkey Madness I"]}

    def test_skill_failure_is_reported_but_not_confused_with_quest_access(self):
        result = eligibility.evaluate_items(self.items, self.requirements, self.profile)
        rows = {row["item_id"]: row for row in result["results"]}
        self.assertEqual(rows[10]["skill_status"], "meets_known_skill_requirements")
        self.assertEqual(rows[10]["overall_status"], "unknown")
        self.assertEqual(rows[11]["skill_status"], "ineligible")
        self.assertEqual(rows[11]["overall_status"], "ineligible_by_known_skill_requirement")
        self.assertIn("Quest, unlock", " ".join(rows[10]["reasons"]))

    def test_missing_requirement_record_never_means_eligible(self):
        result = eligibility.evaluate_items(self.items, self.requirements, self.profile)
        row = next(x for x in result["results"] if x["item_id"] == 12)
        self.assertEqual(row["overall_status"], "unknown")
        self.assertEqual(row["skill_status"], "unknown")

    def test_manual_exclusion_by_id_and_name_wins(self):
        profile = dict(self.profile, excluded_item_ids=[10], excluded_item_names=["excluded BY name"])
        result = eligibility.evaluate_items(self.items, self.requirements, profile)
        rows = {row["item_id"]: row for row in result["results"]}
        self.assertEqual(rows[10]["overall_status"], "excluded")
        self.assertEqual(rows[13]["overall_status"], "excluded")
        self.assertTrue(rows[10]["manual_exclusion"])

    def test_missing_player_skill_is_unknown_not_pass(self):
        result = eligibility.evaluate_items(self.items, self.requirements, {"skills": {"Defence": 40}})
        row = next(x for x in result["results"] if x["item_id"] == 11)
        self.assertEqual(row["skill_status"], "unknown")
        self.assertEqual(row["overall_status"], "unknown")

    def test_invalid_profile_levels_are_reported(self):
        result = eligibility.evaluate_items(self.items, self.requirements, {"skills": {"Defence": True}})
        row = next(x for x in result["results"] if x["item_id"] == 10)
        self.assertEqual(row["overall_status"], "unknown")
        self.assertTrue(result["profile_warnings"])

    def test_requirement_provenance_is_returned_for_auditing(self):
        result = eligibility.evaluate_items(self.items, self.requirements, self.profile)
        row = next(x for x in result["results"] if x["item_id"] == 10)
        self.assertEqual(row["requirement_sources"], ["OSRS Wiki"])
        self.assertEqual(row["requirement_source_urls"], ["https://oldschool.runescape.wiki/w/Rune_platebody"])
        missing = next(x for x in result["results"] if x["item_id"] == 12)
        self.assertEqual(missing["requirement_sources"], [])
        self.assertEqual(missing["requirement_source_urls"], [])

    def test_malformed_exclusion_and_quest_lists_are_not_silently_ignored(self):
        profile = {
            "skills": {"Defence": 50},
            "excluded_item_ids": "10",
            "excluded_item_names": [None, ""],
            "completed_quests": "Monkey Madness I",
        }
        result = eligibility.evaluate_items(self.items, self.requirements, profile)
        self.assertGreaterEqual(len(result["profile_warnings"]), 4)
        self.assertEqual(next(x for x in result["results"] if x["item_id"] == 10)["overall_status"], "unknown")

    def test_duplicate_requirement_records_keep_all_source_attribution(self):
        requirements = self.requirements + [
            {"item_id": 10, "requirements": [{"skill": "Defence", "level": 40}], "sources": ["RuneLite"], "source_url": "http://not-secure.example"}
        ]
        result = eligibility.evaluate_items(self.items, requirements, self.profile)
        row = next(x for x in result["results"] if x["item_id"] == 10)
        self.assertEqual(row["requirement_sources"], ["OSRS Wiki", "RuneLite"])
        self.assertEqual(row["requirement_source_urls"], ["https://oldschool.runescape.wiki/w/Rune_platebody"])

    def test_rejects_non_array_datasets(self):
        with self.assertRaises(ValueError):
            eligibility.evaluate_items({}, [], {"skills": {}})


if __name__ == "__main__":
    unittest.main()
