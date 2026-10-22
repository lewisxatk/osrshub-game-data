import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compare_loadout_upgrade_delta import compare_loadouts

class LoadoutUpgradeDeltaTests(unittest.TestCase):
    def setUp(self):
        self.profiles = [
            {"id": 1, "name": "Bronze sword", "slot": "weapon", "bonuses": {"attack_slash": 5, "melee_strength": 4}, "attack_speed": 4, "skill_requirements": [], "source_urls": ["https://example.invalid/a"], "data_status": "joined_fields_present"},
            {"id": 2, "name": "Steel sword", "slot": "weapon", "bonuses": {"attack_slash": 10, "melee_strength": 8}, "attack_speed": 4, "skill_requirements": [], "source_urls": ["https://example.invalid/b"], "data_status": "joined_fields_present"},
            {"id": 3, "name": "Bronze body", "slot": "body", "bonuses": {"attack_slash": 0, "melee_strength": 1}, "skill_requirements": [], "source_urls": ["https://example.invalid/c"], "data_status": "joined_fields_present"},
        ]
        self.costs = {"1": 100, "2": 500, "3": 100}
        self.inputs = {"effective_attack": 50, "effective_strength": 50, "effective_defence": 50, "defence_bonus": 0}

    def test_delta_uses_same_inputs_and_reports_slot_change(self):
        result = compare_loadouts(self.profiles, [1, 3], [2, 3], self.costs, 1000, self.inputs, "slash")
        self.assertEqual(result["status"], "baseline_upgrade_delta_with_limitations")
        self.assertEqual(result["delta"]["cost_gp"], 400)
        self.assertEqual(result["delta"]["attack_bonus"], 5)
        self.assertEqual(result["delta"]["melee_strength"], 4)
        self.assertEqual(len(result["slot_changes"]), 1)
        self.assertEqual(result["slot_changes"][0]["slot"], "weapon")
        self.assertGreater(result["delta"]["dps"], 0)

    def test_candidate_over_budget_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "exceeding budget"):
            compare_loadouts(self.profiles, [1, 3], [2, 3], self.costs, 200, self.inputs, "slash")

    def test_duplicate_slot_is_rejected_by_existing_evaluator(self):
        with self.assertRaisesRegex(ValueError, "multiple selected items occupy slot"):
            compare_loadouts(self.profiles, [1, 3], [1, 2, 3], self.costs, 1000, self.inputs, "slash")

if __name__ == "__main__":
    unittest.main()
