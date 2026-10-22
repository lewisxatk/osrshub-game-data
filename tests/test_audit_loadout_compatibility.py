"""Regression tests for database-only selected-loadout compatibility auditing."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_loadout_compatibility import evaluate_loadout, index_profiles


def profile(item_id=4151, name="Abyssal whip", slot="weapon", requirements=None, **overrides):
    row = {
        "id": item_id, "name": name, "slot": slot,
        "bonuses": {"attack_slash": 82, "melee_strength": 82},
        "attack_speed": 4, "weapon_type": "whip", "stances": [],
        "skill_requirements": [{"skill": "Attack", "level": 70}] if requirements is None else requirements,
        "equipment_record_present": True, "weapon_record_present": True,
        "skill_requirement_record_present": True,
        "source_urls": ["https://example.test/item"], "sources": ["fixture"],
        "data_status": "joined_fields_present",
    }
    row.update(overrides)
    return row


class LoadoutCompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.profiles = index_profiles([profile()])
        self.player = {"skills": {"Attack": 80}, "completed_quests": [], "excluded_item_ids": [], "excluded_item_names": []}

    def test_known_requirements_and_slot_pass(self):
        result = evaluate_loadout({"items": [{"item_id": 4151, "slot": "weapon"}]}, self.profiles, self.player)
        self.assertEqual(result["status"], "passed_known_checks")
        self.assertEqual(result["results"][0]["status"], "meets_known_checks")

    def test_slot_mismatch_is_fatal_and_explicit(self):
        result = evaluate_loadout({"items": [{"item_id": 4151, "slot": "head"}]}, self.profiles, self.player)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any(e["code"] == "slot_mismatch" for e in result["errors"]))

    def test_duplicate_slot_and_item_are_detected(self):
        result = evaluate_loadout({"items": [{"item_id": 4151, "slot": "weapon"}, {"item_id": 4151, "slot": "weapon"}]}, self.profiles, self.player)
        codes = {e["code"] for e in result["errors"]}
        self.assertIn("duplicate_item_id", codes)
        self.assertIn("duplicate_slot", codes)

    def test_missing_profile_is_not_eligible(self):
        result = evaluate_loadout([99999], self.profiles, self.player)
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["results"][0]["status"], "unknown")

    def test_unmet_skill_requirement_is_ineligible(self):
        self.player["skills"]["Attack"] = 60
        result = evaluate_loadout([4151], self.profiles, self.player)
        self.assertEqual(result["status"], "review_required")
        self.assertEqual(result["results"][0]["status"], "ineligible_by_known_skill_requirement")

    def test_missing_requirement_record_stays_unknown(self):
        rows = index_profiles([profile(skill_requirement_record_present=False, skill_requirements=None)])
        result = evaluate_loadout([4151], rows, self.player)
        self.assertEqual(result["status"], "review_required")
        self.assertEqual(result["results"][0]["status"], "review_required")

    def test_missing_player_skill_stays_unknown(self):
        result = evaluate_loadout([4151], self.profiles, {"skills": {}})
        self.assertEqual(result["status"], "review_required")
        self.assertEqual(result["results"][0]["status"], "review_required")

    def test_manual_exclusion_wins(self):
        player = dict(self.player, excluded_item_ids=[4151])
        result = evaluate_loadout([4151], self.profiles, player)
        self.assertEqual(result["results"][0]["status"], "excluded")

    def test_budget_overrun_detected(self):
        result = evaluate_loadout([4151], self.profiles, self.player, {"4151": 101}, budget=100)
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any(e["code"] == "budget_overrun" for e in result["errors"]))

    def test_unknown_cost_does_not_claim_budget_pass(self):
        result = evaluate_loadout([4151], self.profiles, self.player, {}, budget=100)
        self.assertEqual(result["status"], "review_required")
        self.assertIsNone(result["results"][0]["cost_gp"])

    def test_duplicate_dataset_ids_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate item ID"):
            index_profiles([profile(), profile()])

    def test_non_array_dataset_rejected(self):
        with self.assertRaisesRegex(ValueError, "JSON array"):
            index_profiles({})

    def test_malformed_profile_level_is_warning(self):
        result = evaluate_loadout([4151], self.profiles, {"skills": {"Attack": True}})
        self.assertEqual(result["status"], "review_required")
        self.assertTrue(result["profile_warnings"])


if __name__ == "__main__":
    unittest.main()
