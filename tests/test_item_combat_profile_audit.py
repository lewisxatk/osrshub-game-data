"""Regression tests for the joined item-combat-profile checker."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_item_combat_profiles import audit_profiles, BONUS_FIELDS


def profile(**overrides):
    row = {
        "id": 4151,
        "name": "Abyssal whip",
        "bonuses": {field: 0 for field in BONUS_FIELDS},
        "attack_speed": 4,
        "equipment_record_present": True,
        "weapon_record_present": True,
        "skill_requirement_record_present": True,
        "skill_requirements": [{"skill": "Attack", "level": 70}],
        "source_urls": ["https://oldschool.runescape.wiki/w/Abyssal_whip"],
        "data_status": "joined_fields_present",
    }
    row.update(overrides)
    return row


class ItemCombatProfileAuditTests(unittest.TestCase):
    def test_valid_profile_passes(self):
        report = audit_profiles([profile()])
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["error_count"], 0)

    def test_non_finite_numeric_string_fails(self):
        row = profile()
        row["bonuses"]["melee_strength"] = "NaN"
        report = audit_profiles([row])
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any(issue.get("issue") == "non_finite_or_non_numeric_bonus"
                            for issue in report["errors"]))

    def test_malformed_source_url_fails(self):
        report = audit_profiles([profile(source_urls=["https://"])])
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any(issue.get("issue") == "invalid_source_urls"
                            for issue in report["errors"]))

    def test_skill_requirement_above_game_cap_fails(self):
        report = audit_profiles([profile(skill_requirements=[{"skill": "Attack", "level": 100}])])
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any(issue.get("issue") == "invalid_requirement"
                            for issue in report["errors"]))

    def test_unknown_bonuses_remain_warnings_not_zero(self):
        row = profile()
        row["bonuses"]["magic_damage"] = None
        report = audit_profiles([row])
        self.assertEqual(report["status"], "review_required")
        self.assertEqual(row["bonuses"]["magic_damage"], None)


if __name__ == "__main__":
    unittest.main()
