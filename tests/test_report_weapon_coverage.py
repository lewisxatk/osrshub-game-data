"""Regression tests for generated weapon-profile coverage reporting."""
import unittest

from scripts.report_weapon_coverage import summarize_profiles


class WeaponCoverageTests(unittest.TestCase):
    def profile(self, item_id=1, **overrides):
        row = {
            "id": item_id, "name": "Test weapon", "slot": "weapon",
            "bonuses": {"attack_slash": 10, "melee_strength": 8},
            "attack_speed": 4, "weapon_type": "sword", "stances": [],
            "skill_requirements": [{"skill": "attack", "level": 1}],
            "skill_requirement_record_present": True,
            "source_urls": ["https://example.invalid/source"], "sources": ["fixture"],
            "weapon_record_present": True,
        }
        row.update(overrides)
        return row

    def test_reports_presence_and_numeric_bonus_coverage(self):
        result = summarize_profiles([self.profile(), self.profile(2, bonuses={"attack_slash": None})])
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["counts"]["weapon_profiles"], 2)
        self.assertEqual(result["field_coverage"]["attack_speed"]["coverage_percent"], 100.0)
        self.assertEqual(result["bonus_coverage"]["attack_slash"]["numeric_count"], 1)

    def test_missing_requirement_record_is_reported_not_inferred(self):
        result = summarize_profiles([self.profile(skill_requirement_record_present=False)])
        self.assertEqual(result["counts"]["missing_requirement_record_count"], 1)
        self.assertIn("unknown", " ".join(result["guardrails"]).lower())

    def test_duplicate_ids_fail_closed(self):
        result = summarize_profiles([self.profile(), self.profile()])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["counts"]["record_errors"], 1)
        self.assertEqual(result["quality_samples"]["record_errors"][0]["issue"], "duplicate_item_id")

    def test_invalid_attack_speed_is_reported(self):
        result = summarize_profiles([self.profile(attack_speed=0)])
        self.assertEqual(result["counts"]["invalid_attack_speed_count"], 1)

    def test_non_object_dataset_rows_are_reported(self):
        result = summarize_profiles([self.profile(), "bad row"])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["quality_samples"]["record_errors"][0]["issue"], "record_not_object")


if __name__ == "__main__":
    unittest.main()
