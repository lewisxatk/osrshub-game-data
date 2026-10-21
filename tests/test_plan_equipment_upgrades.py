"""Tests for price-input-driven, conservative equipment shortlist planning."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from plan_equipment_upgrades import build_plan

class EquipmentUpgradePlanTests(unittest.TestCase):
    def setUp(self):
        self.equipment = [
            {"id": 1, "name": "Basic helm", "slot": "head", "bonuses": {"attack_slash": 2}},
            {"id": 2, "name": "Strong helm", "slot": "head", "bonuses": {"attack_slash": 10}},
            {"id": 3, "name": "Expensive helm", "slot": "head", "bonuses": {"attack_slash": 20}},
            {"id": 4, "name": "Mystery helm", "slot": "head", "bonuses": {"attack_slash": 8}},
            {"id": 5, "name": "Magic top", "slot": "body", "bonuses": {"attack_magic": 15}},
        ]
        self.requirements = [
            {"item_id": 1, "requirements": [{"skill": "Defence", "level": 1}]},
            {"item_id": 2, "requirements": [{"skill": "Defence", "level": 40}]},
            {"item_id": 3, "requirements": [{"skill": "Defence", "level": 70}]},
        ]
        self.profile = {"skills": {"Defence": 50}, "excluded_item_ids": [], "excluded_item_names": []}
        self.costs = {"1": 100, "2": 1000, "3": 10000, "4": 200}

    def test_ranks_by_objective_and_respects_budget(self):
        result = build_plan(self.equipment, self.requirements, self.profile, self.costs, 1500, "attack_slash")
        rows = result["results_by_slot"]["head"]
        self.assertEqual([x["item_id"] for x in rows[:2]], [2, 4])
        self.assertIn("over_budget", [x["status"] for x in rows])
        self.assertEqual(result["status"], "candidate_shortlist_only")

    def test_manual_exclusion_removes_item_from_usable_candidate_ranking(self):
        profile = dict(self.profile, excluded_item_ids=[2])
        result = build_plan(self.equipment, self.requirements, profile, self.costs, 1500, "attack_slash")
        rows = result["results_by_slot"]["head"]
        excluded = next(x for x in rows if x["item_id"] == 2)
        self.assertEqual(excluded["status"], "excluded")

    def test_known_skill_failure_is_marked_ineligible(self):
        result = build_plan(self.equipment, self.requirements, self.profile, self.costs, 20000, "attack_slash")
        rows = result["results_by_slot"]["head"]
        strong = next(x for x in rows if x["item_id"] == 3)
        self.assertEqual(strong["status"], "ineligible_by_known_skill_requirement")

    def test_missing_cost_or_requirement_is_unknown_not_eligible(self):
        result = build_plan(self.equipment, self.requirements, self.profile, self.costs, 1500, "attack_slash")
        mystery = next(x for x in result["results_by_slot"]["head"] if x["item_id"] == 4)
        self.assertEqual(mystery["status"], "candidate_with_unknown_restrictions")
        self.assertTrue(any("No normalized" in x for x in mystery["reasons"]))
        body = next(x for x in result["results_by_slot"]["body"] if x["item_id"] == 5)
        self.assertEqual(body["status"], "unknown")
        self.assertIsNone(body["cost"])

    def test_invalid_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            build_plan([], [], [], {}, 100, "attack_slash")
        with self.assertRaises(ValueError):
            build_plan([], [], {}, {}, -1, "attack_slash")
        with self.assertRaises(ValueError):
            build_plan([], [], {}, {}, 100, "dps")

if __name__ == "__main__":
    unittest.main()
