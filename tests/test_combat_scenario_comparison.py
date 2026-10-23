import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from compare_combat_scenarios import compare_scenarios


def eq(i, name, slot, attack, strength, speed=None):
    return {
        "id": i, "name": name, "slot": slot,
        "bonuses": {
            "attack_stab": attack, "attack_slash": attack,
            "attack_crush": attack, "melee_strength": strength,
        },
        "attack_speed": speed, "source_urls": ["https://oldschool.runescape.wiki/w/Test"],
    }


def prof(i, name, slot, attack, strength, speed=None):
    return {
        "id": i, "name": name, "slot": slot,
        "bonuses": {
            "attack_stab": attack, "attack_slash": attack,
            "attack_crush": attack, "melee_strength": strength,
        },
        "attack_speed": speed, "skill_requirements": [],
        "source_urls": ["https://oldschool.runescape.wiki/w/Test"],
        "data_status": "joined_fields_present",
    }


class CombatScenarioComparisonTests(unittest.TestCase):
    def setUp(self):
        self.equipment = [
            eq(1, "Slow sword", "weapon", 50, 40, 6),
            eq(2, "Fast sword", "weapon", 40, 35, 4),
            eq(3, "Good helm", "head", 10, 5),
        ]
        self.requirements = [
            {"item_id": i, "requirements_status": "known_empty", "requirements": []}
            for i in (1, 2, 3)
        ]
        self.unlocks = [
            {"item_id": i, "requirements_status": "known_empty", "required_quests": [],
             "source_url": "https://oldschool.runescape.wiki/w/Test_fixture_source"}
            for i in (1, 2, 3)
        ]
        self.profiles = [
            prof(1, "Slow sword", "weapon", 50, 40, 6),
            prof(2, "Fast sword", "weapon", 40, 35, 4),
            prof(3, "Good helm", "head", 10, 5),
        ]
        self.account = {
            "skills": {"Attack": 99, "Strength": 99, "Defence": 99},
            "completed_quests": [], "current_equipment": {"weapon": 1},
        }
        self.costs = {"1": 1000, "2": 2000, "3": 500}
        self.scenarios = [
            {
                "scenario_id": "high-defence", "name": "Illustrative high defence",
                "combat_inputs": {"effective_attack": 100, "effective_strength": 100,
                                  "effective_defence": 120, "defence_bonus": 120},
                "weight": 2, "source_url": "https://oldschool.runescape.wiki/w/Combat",
            },
            {
                "scenario_id": "low-defence", "name": "Illustrative low defence",
                "combat_inputs": {"effective_attack": 100, "effective_strength": 100,
                                  "effective_defence": 40, "defence_bonus": 20},
                "weight": 1, "source_url": "https://oldschool.runescape.wiki/w/Combat",
            },
        ]

    def run_compare(self, **kwargs):
        return compare_scenarios(
            self.equipment, self.requirements, self.unlocks, self.profiles,
            self.account, self.costs, 4000, self.scenarios, **kwargs
        )

    def test_ranks_candidates_across_every_scenario(self):
        result = self.run_compare()
        self.assertIn(result["status"], ("scenario_ranked_candidates", "search_truncated"))
        self.assertEqual(result["scenario_count"], 2)
        self.assertGreater(result["evaluated_candidate_count"], 0)
        candidate = result["ranked_candidates"][0]
        self.assertEqual(len(candidate["scenario_results"]), 2)
        self.assertGreaterEqual(candidate["best_case_dps"], candidate["worst_case_dps"])
        self.assertAlmostEqual(
            candidate["dps_spread"],
            candidate["best_case_dps"] - candidate["worst_case_dps"],
        )

    def test_scenario_weights_are_normalized(self):
        result = self.run_compare()
        self.assertAlmostEqual(sum(s["normalized_weight"] for s in result["scenarios"]), 1.0)
        self.assertAlmostEqual(result["scenarios"][0]["normalized_weight"], 2 / 3)

    def test_all_ranked_loadouts_obey_budget(self):
        result = self.run_compare()
        for candidate in result["ranked_candidates"]:
            self.assertLessEqual(candidate["total_cost_gp"], 4000)
            self.assertEqual(candidate["remaining_budget_gp"], 4000 - candidate["total_cost_gp"])

    def test_duplicate_scenario_ids_rejected(self):
        scenarios = [dict(self.scenarios[0]), dict(self.scenarios[1])]
        scenarios[1]["scenario_id"] = scenarios[0]["scenario_id"]
        with self.assertRaisesRegex(ValueError, "duplicate scenario_id"):
            self.run_compare_scenarios(scenarios)

    def test_non_wiki_source_rejected(self):
        scenarios = [dict(self.scenarios[0]), dict(self.scenarios[1])]
        scenarios[0]["source_url"] = "https://example.com/not-evidence"
        with self.assertRaisesRegex(ValueError, "OSRS Wiki source_url"):
            self.run_compare_scenarios(scenarios)

    def test_lookalike_wiki_hostname_rejected(self):
        scenarios = [dict(self.scenarios[0]), dict(self.scenarios[1])]
        scenarios[0]["source_url"] = "https://oldschool.runescape.wiki.attacker.example/w/Combat"
        with self.assertRaisesRegex(ValueError, "OSRS Wiki source_url"):
            self.run_compare_scenarios(scenarios)

    def test_boolean_weight_rejected(self):
        scenarios = [dict(self.scenarios[0]), dict(self.scenarios[1])]
        scenarios[0]["weight"] = True
        with self.assertRaisesRegex(ValueError, "finite positive number"):
            self.run_compare_scenarios(scenarios)

    def test_missing_input_rejected(self):
        scenarios = [dict(self.scenarios[0]), dict(self.scenarios[1])]
        scenarios[0]["combat_inputs"] = {"effective_attack": 100}
        with self.assertRaisesRegex(ValueError, "missing combat inputs"):
            self.run_compare_scenarios(scenarios)

    def test_too_few_scenarios_rejected(self):
        with self.assertRaisesRegex(ValueError, "between 2 and 10"):
            self.run_compare_scenarios([self.scenarios[0]])

    def test_node_limit_truncation_is_visible(self):
        result = self.run_compare(node_limit=1)
        self.assertEqual(result["status"], "search_truncated")
        self.assertTrue(any(row["search"]["truncated"] for row in result["scenario_searches"]))

    def run_compare_scenarios(self, scenarios):
        return compare_scenarios(
            self.equipment, self.requirements, self.unlocks, self.profiles,
            self.account, self.costs, 4000, scenarios,
        )


if __name__ == "__main__":
    unittest.main()
