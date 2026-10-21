"""Tests for item combat profile audit guardrails."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_item_combat_profiles import audit_profiles

def profile(**updates):
    row = {
        "id": 4151, "name": "Abyssal whip", "slot": "weapon",
        "bonuses": {"attack_stab": 0, "attack_slash": 82, "attack_crush": 0, "attack_magic": 0, "attack_ranged": 0,
                    "defence_stab": 0, "defence_slash": 0, "defence_crush": 0, "defence_magic": 0, "defence_ranged": 0,
                    "melee_strength": 82, "ranged_strength": 0, "magic_damage": 0, "prayer": 0},
        "attack_speed": 4, "weapon_type": "whip", "stances": [],
        "skill_requirements": [{"skill": "Attack", "level": 70}],
        "equipment_record_present": True, "weapon_record_present": True, "skill_requirement_record_present": True,
        "source_urls": ["https://oldschool.runescape.wiki/w/Abyssal_whip"], "sources": ["fixture"],
        "data_status": "joined_fields_present"
    }
    row.update(updates)
    return row

class ItemCombatProfileAuditTests(unittest.TestCase):
    def test_complete_fixture_passes(self):
        report = audit_profiles([profile()])
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["with_positive_attack_speed"], 1)

    def test_null_stats_are_reviewed_not_silently_zeroed(self):
        row = profile(bonuses={**profile()["bonuses"], "attack_stab": None})
        report = audit_profiles([row])
        self.assertEqual(report["status"], "review_required")
        self.assertTrue(any(w["issue"] == "incomplete_bonus_coverage" for w in report["warnings"]))

    def test_invalid_speed_fails(self):
        report = audit_profiles([profile(attack_speed=0)])
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any(e.get("issue") == "invalid_attack_speed" for e in report["errors"]))

    def test_duplicate_skill_requirement_fails(self):
        row = profile(skill_requirements=[{"skill":"Attack","level":70},{"skill":" attack ","level":70}])
        report = audit_profiles([row])
        self.assertTrue(any(e.get("issue") == "duplicate_skill_requirement" for e in report["errors"]))

    def test_no_source_link_requires_review(self):
        report = audit_profiles([profile(source_urls=[])])
        self.assertEqual(report["status"], "review_required")
        self.assertEqual(report["with_source_urls"], 0)

    def test_duplicate_item_ids_fail(self):
        report = audit_profiles([profile(), profile()])
        self.assertTrue(any(e.get("issue") == "duplicate_item_id" for e in report["errors"]))

if __name__ == "__main__":
    unittest.main()
