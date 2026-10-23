import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from plan_combat_studio_upgrades import plan_upgrades

class CombatStudioUpgradePlanTests(unittest.TestCase):
    def setUp(self):
        self.equipment = [
            {"id": 1, "name": "Bronze sword", "slot": "weapon", "bonuses": {"attack_slash": 5, "melee_strength": 4}},
            {"id": 2, "name": "Steel sword", "slot": "weapon", "bonuses": {"attack_slash": 10, "melee_strength": 8}},
            {"id": 3, "name": "Bronze body", "slot": "body", "bonuses": {"attack_slash": 0, "melee_strength": 1}},
        ]
        self.requirements = [{"item_id": i, "requirements_status": "known_empty", "requirements": []} for i in (1, 2, 3)]
        self.unlocks = [{"item_id": i, "requirements_status": "known_empty", "required_quests": []} for i in (1, 2, 3)]
        self.profiles = [
            {"id": 1, "name": "Bronze sword", "slot": "weapon", "bonuses": {"attack_slash": 5, "melee_strength": 4}, "attack_speed": 4, "skill_requirements": [], "source_urls": [], "data_status": "joined_fields_present"},
            {"id": 2, "name": "Steel sword", "slot": "weapon", "bonuses": {"attack_slash": 10, "melee_strength": 8}, "attack_speed": 4, "skill_requirements": [], "source_urls": [], "data_status": "joined_fields_present"},
            {"id": 3, "name": "Bronze body", "slot": "body", "bonuses": {"attack_slash": 0, "melee_strength": 1}, "attack_speed": 4, "skill_requirements": [], "source_urls": [], "data_status": "joined_fields_present"},
        ]
        self.profile = {"skills": {}, "completed_quests": [], "current_equipment": {"weapon": 1, "body": 3}}
        self.costs = {"1": 100, "2": 500, "3": 100}
        self.inputs = {"effective_attack": 50, "effective_strength": 50, "effective_defence": 50, "defence_bonus": 0}

    def make_plan(self, baseline=None):
        return plan_upgrades(self.equipment, self.requirements, self.unlocks, self.profiles,
            self.profile, baseline or [1, 3], self.costs, 1000, self.inputs, "slash")

    def test_owned_gear_is_free_and_upgrade_is_ranked(self):
        result = self.make_plan()
        self.assertEqual(result["status"], "upgrade_recommendations_with_limitations")
        self.assertEqual(result["baseline"]["total_cost_gp"], 0)
        self.assertTrue(any(2 in [item["item_id"] for item in row["selected_items"]] for row in result["recommendations"]))
        self.assertGreater(result["recommendations"][0]["dps_gain"], 0)
        self.assertTrue(all(row["dps_gain"] > 0 for row in result["recommendations"]))
        self.assertEqual(result["recommendations"][0]["upgrade_cost_gp"], 500)
        comparison = result["recommendations"][0]["combat_comparison"]
        self.assertAlmostEqual(comparison["delta"]["dps"], result["recommendations"][0]["dps_gain"], places=7)
        self.assertGreater(comparison["candidate"]["attack_roll"], comparison["baseline"]["attack_roll"])
        self.assertGreater(comparison["delta"]["max_hit"], 0)
        self.assertEqual(comparison["candidate"]["attack_speed_ticks"], 4)

    def test_no_improving_change_is_not_called_an_upgrade(self):
        # With the stronger candidate removed, every changed combination is
        # equal or worse than the current gear and must not be recommended.
        equipment = [row for row in self.equipment if row["id"] != 2]
        profiles = [row for row in self.profiles if row["id"] != 2]
        requirements = [row for row in self.requirements if row["item_id"] != 2]
        unlocks = [row for row in self.unlocks if row["item_id"] != 2]
        result = plan_upgrades(equipment, requirements, unlocks, profiles, self.profile,
            [1, 3], self.costs, 1000, self.inputs, "slash")
        self.assertEqual(result["status"], "no_improving_upgrade_found")
        self.assertEqual(result["recommendations"], [])

    def test_duplicate_baseline_ids_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicates"):
            self.make_plan([1, 1])

if __name__ == "__main__":
    unittest.main()
