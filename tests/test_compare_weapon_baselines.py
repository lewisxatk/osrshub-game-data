"""Tests for baseline weapon comparisons."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compare_weapon_baselines import compare_weapons

class WeaponBaselineTests(unittest.TestCase):
    def setUp(self):
        self.weapons = [
            {"id": 10, "name": "Quick blade", "attack_speed": 4, "source_url": "https://example.test/quick"},
            {"id": 11, "name": "Heavy blade", "attack_speed": 5, "source_url": "https://example.test/heavy"},
            {"id": 12, "name": "Too slow", "attack_speed": None},
        ]
        self.equipment = [
            {"id": 10, "name": "Quick blade", "bonuses": {"attack_slash": 80, "melee_strength": 70}},
            {"id": 11, "name": "Heavy blade", "bonuses": {"attack_slash": 120, "melee_strength": 100}},
            {"id": 12, "name": "Too slow", "bonuses": {"attack_slash": 50, "melee_strength": 40}},
        ]
        self.requirements = [
            {"item_id": 10, "requirements": [{"skill": "Attack", "level": 60}]},
            {"item_id": 11, "requirements": [{"skill": "Attack", "level": 80}]},
        ]
        self.profile = {"skills": {"Attack": 75}, "excluded_item_ids": [], "excluded_item_names": []}
        self.costs = {"10": 1000, "11": 9000, "12": 100}
        self.inputs = {"effective_attack": 100, "effective_strength": 100, "effective_defence": 80, "defence_bonus": 80}

    def test_computes_and_sorts_baseline_candidates(self):
        result = compare_weapons(self.weapons, self.equipment, self.requirements, self.profile, self.costs, self.inputs, 10000, "slash")
        self.assertEqual(result["status"], "baseline_comparison_only")
        self.assertEqual(result["results"][0]["item_id"], 10)
        self.assertGreater(result["results"][0]["dps"], 0)
        self.assertIn("not modelled", " ".join(result["results"][0]["reasons"]))
        self.assertEqual(result["results"][0]["baseline_rank"], 1)
        self.assertGreater(result["results"][0]["dps_per_million_gp"], 0)
        self.assertEqual(result["comparable_candidate_count"], 1)

    def test_known_skill_failure_is_not_ranked_as_comparable(self):
        result = compare_weapons(self.weapons, self.equipment, self.requirements, self.profile, self.costs, self.inputs, 10000, "slash")
        heavy = next(row for row in result["results"] if row["item_id"] == 11)
        self.assertEqual(heavy["status"], "ineligible_by_known_skill_requirement")

    def test_budget_and_manual_exclusions_apply(self):
        profile = dict(self.profile, excluded_item_ids=[10])
        result = compare_weapons(self.weapons, self.equipment, self.requirements, profile, self.costs, self.inputs, 500, "slash")
        statuses = {row["item_id"]: row["status"] for row in result["results"]}
        self.assertEqual(statuses[10], "excluded")
        self.assertEqual(statuses[11], "over_budget")

    def test_missing_stats_stay_unknown(self):
        result = compare_weapons(self.weapons, self.equipment, self.requirements, self.profile, self.costs, self.inputs, 10000, "slash")
        slow = next(row for row in result["results"] if row["item_id"] == 12)
        self.assertEqual(slow["status"], "unknown")
        self.assertTrue(slow["reasons"])

    def test_fractional_equipment_bonus_is_not_silently_truncated(self):
        equipment = [dict(row) for row in self.equipment]
        equipment[0] = {**equipment[0], "bonuses": {"attack_slash": 80.5, "melee_strength": 70}}
        result = compare_weapons(self.weapons, equipment, self.requirements, self.profile, self.costs, self.inputs, 10000, "slash")
        row = next(item for item in result["results"] if item["item_id"] == 10)
        self.assertEqual(row["status"], "unknown")
        self.assertIn("Missing valid attack speed", " ".join(row["reasons"]))

    def test_zero_cost_does_not_divide_by_zero(self):
        costs = dict(self.costs, **{"10": 0})
        result = compare_weapons(self.weapons, self.equipment, self.requirements, self.profile, costs, self.inputs, 10000, "slash")
        row = next(item for item in result["results"] if item["item_id"] == 10)
        self.assertIsNone(row["dps_per_million_gp"])

    def test_rejects_invalid_inputs(self):
        with self.assertRaises(ValueError):
            compare_weapons([], [], [], {}, {}, {}, -1, "slash")
        with self.assertRaises(ValueError):
            compare_weapons([], [], [], {}, {}, self.inputs, 100, "magic")

if __name__ == "__main__":
    unittest.main()
