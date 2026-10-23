"""Tests for the account-aware, budgeted Combat Studio planning foundation."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_combat_studio_plan import build_plan

class CombatStudioPlanTests(unittest.TestCase):
    def setUp(self):
        self.equipment = [
            {"id": 1, "name": "Starter helm", "slot": "head", "bonuses": {"melee_strength": 1}, "source_urls": ["https://example.test/1"]},
            {"id": 2, "name": "Quest helm", "slot": "head", "bonuses": {"melee_strength": 8}},
            {"id": 3, "name": "Better helm", "slot": "head", "bonuses": {"melee_strength": 5}},
            {"id": 4, "name": "Mystery helm", "slot": "head", "bonuses": {"melee_strength": 20}},
            {"id": 5, "name": "Body", "slot": "body", "bonuses": {"melee_strength": 4}},
            {"id": 6, "name": "Excluded body", "slot": "body", "bonuses": {"melee_strength": 99}},
        ]
        self.requirements = [
            {"item_id": 1, "requirements_status": "known_empty", "requirements": []},
            {"item_id": 2, "requirements_status": "known", "requirements": [{"skill": "Defence", "level": 40}]},
            {"item_id": 3, "requirements_status": "known", "requirements": [{"skill": "Defence", "level": 40}]},
            {"item_id": 5, "requirements_status": "known_empty", "requirements": []},
            {"item_id": 6, "requirements_status": "known_empty", "requirements": []},
        ]
        self.unlocks = [
            {"item_id": 1, "requirements_status": "known_empty", "required_quests": [], "source_url": "https://oldschool.runescape.wiki/w/Test_fixture_source"},
            {"item_id": 2, "requirements_status": "known", "required_quests": ["Monkey Madness I"], "source_url": "https://oldschool.runescape.wiki/w/Test_fixture_source"},
            {"item_id": 3, "requirements_status": "known_empty", "required_quests": [], "source_url": "https://oldschool.runescape.wiki/w/Test_fixture_source"},
            {"item_id": 5, "requirements_status": "known_empty", "required_quests": [], "source_url": "https://oldschool.runescape.wiki/w/Test_fixture_source"},
            {"item_id": 6, "requirements_status": "known_empty", "required_quests": [], "source_url": "https://oldschool.runescape.wiki/w/Test_fixture_source"},
        ]
        self.profile = {"skills": {"Defence": 50}, "completed_quests": [], "excluded_item_ids": [6],
                        "excluded_item_names": [], "current_equipment": {"head": 1}}
        self.costs = {"1": 100, "2": 5000, "3": 1000, "4": 100, "5": 500, "6": 10}

    def plan(self, budget=1500, **kwargs):
        return build_plan(self.equipment, self.requirements, self.unlocks, self.profile, self.costs, budget, **kwargs)

    def test_quest_locked_item_is_excluded_with_reason_and_alternative_selected(self):
        result = self.plan()
        audit = {x["item_id"]: x for x in result["audit"]}
        self.assertEqual(audit[2]["status"], "ineligible")
        self.assertIn("Monkey Madness I", " ".join(audit[2]["reasons"]))
        self.assertIn(3, [x["item_id"] for x in result["selected_items"]])

    def test_unknown_requirement_data_never_becomes_eligible(self):
        result = self.plan()
        mystery = next(x for x in result["audit"] if x["item_id"] == 4)
        self.assertEqual(mystery["status"], "unknown")
        self.assertNotIn(4, [x["item_id"] for x in result["selected_items"]])

    def test_manual_exclusion_wins_over_high_bonus(self):
        result = self.plan()
        excluded = next(x for x in result["audit"] if x["item_id"] == 6)
        self.assertEqual(excluded["status"], "excluded")
        self.assertNotIn(6, [x["item_id"] for x in result["selected_items"]])

    def test_current_item_is_zero_cost_and_upgrade_path_reports_delta(self):
        result = self.plan()
        starter = next(x for x in result["audit"] if x["item_id"] == 1)
        self.assertEqual(starter["upgrade_cost_gp"], 0)
        head = next(x for x in result["upgrade_path"] if x["slot"] == "head")
        self.assertEqual(head["from_item_id"], 1)
        self.assertEqual(head["to_item_id"], 3)
        self.assertEqual(head["objective_delta"], 4)

    def test_added_item_flag_does_not_bypass_restrictions(self):
        profile = dict(self.profile, added_item_ids=[2])
        result = build_plan(self.equipment, self.requirements, self.unlocks, profile, self.costs, 10000)
        quest_item = next(x for x in result["audit"] if x["item_id"] == 2)
        self.assertTrue(quest_item["user_added_candidate"])
        self.assertEqual(quest_item["status"], "ineligible")

    def test_missing_unlock_record_is_unknown_and_excluded_from_selection(self):
        unlocks = [x for x in self.unlocks if x["item_id"] != 3]
        result = build_plan(self.equipment, self.requirements, unlocks, self.profile, self.costs, 1200)
        row = next(x for x in result["audit"] if x["item_id"] == 3)
        self.assertEqual(row["status"], "unknown")
        self.assertNotIn(3, [x["item_id"] for x in result["selected_items"]])

    def test_budget_is_upgrade_budget_and_limits_combination(self):
        result = self.plan(budget=400)
        self.assertLessEqual(result["upgrade_cost_gp"], 400)
        self.assertEqual(result["remaining_budget_gp"], 400 - result["upgrade_cost_gp"])

    def test_duplicate_ids_and_invalid_inputs_are_handled(self):
        duplicate = self.equipment + [dict(self.equipment[0])]
        result = build_plan(duplicate, self.requirements, self.unlocks, self.profile, self.costs, 1200)
        self.assertEqual(sum(x["item_id"] == 1 for x in result["audit"]), 1)
        with self.assertRaises(ValueError):
            build_plan([], [], [], {}, {}, -1)
        with self.assertRaises(ValueError):
            build_plan([], [], [], {}, {}, 100, objective="dps")

if __name__ == "__main__":
    unittest.main()
