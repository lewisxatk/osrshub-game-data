"""Tests for cost/DPS Pareto frontier analysis."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from analyze_combat_upgrade_frontier import analyze_frontier


def plan():
    return {
        "status": "fixture",
        "attack_style": "slash",
        "upgrade_budget_gp": 1000,
        "recommendations": [
            {"rank": 1, "dps_gain": 2.0, "upgrade_cost_gp": 900, "dps_gain_percent": 20.0,
             "remaining_budget_gp": 100, "dps_gain_per_million_gp": 2222.22,
             "weapon": "A", "selected_items": [{"item_id": 1}], "slot_changes": [], "warnings": []},
            {"rank": 2, "dps_gain": 1.0, "upgrade_cost_gp": 400, "dps_gain_percent": 10.0,
             "remaining_budget_gp": 600, "dps_gain_per_million_gp": 2500.0,
             "weapon": "B", "selected_items": [{"item_id": 2}], "slot_changes": [], "warnings": []},
            {"rank": 3, "dps_gain": 0.5, "upgrade_cost_gp": 500, "dps_gain_percent": 5.0,
             "remaining_budget_gp": 500, "dps_gain_per_million_gp": 1000.0,
             "weapon": "C", "selected_items": [{"item_id": 3}], "slot_changes": [], "warnings": []},
            {"rank": 4, "dps_gain": 1.5, "upgrade_cost_gp": 400, "dps_gain_percent": 15.0,
             "remaining_budget_gp": 600, "dps_gain_per_million_gp": 3750.0,
             "weapon": "D", "selected_items": [{"item_id": 4}], "slot_changes": [], "warnings": []},
        ]
    }


class CombatUpgradeFrontierTests(unittest.TestCase):
    def test_pareto_frontier_keeps_non_dominated_tradeoffs(self):
        result = analyze_frontier(plan())
        self.assertEqual(result["status"], "frontier_available")
        self.assertEqual({row["rank"] for row in result["frontier"]}, {1, 4})
        self.assertEqual({row["rank"] for row in result["dominated_candidates"]}, {2, 3})

    def test_best_dps_and_efficiency_are_distinct_metrics(self):
        result = analyze_frontier(plan())
        self.assertEqual(result["best_dps_gain_candidate"]["rank"], 1)
        self.assertEqual(result["best_efficiency_candidate"]["rank"], 4)

    def test_zero_cost_candidate_does_not_divide_by_zero(self):
        value = plan()
        value["recommendations"].append({
            "rank": 5, "dps_gain": 0.25, "upgrade_cost_gp": 0, "selected_items": [{"item_id": 5}]
        })
        result = analyze_frontier(value)
        self.assertEqual(len(result["zero_cost_positive_gain_candidates"]), 1)
        self.assertIsNone(result["zero_cost_positive_gain_candidates"][0]["dps_gain_per_million_gp"])

    def test_non_positive_gain_is_excluded(self):
        value = plan()
        value["recommendations"].append({"rank": 6, "dps_gain": 0, "upgrade_cost_gp": 1})
        result = analyze_frontier(value)
        self.assertEqual(result["excluded_counts"]["non_positive_gain"], 1)

    def test_over_budget_candidate_is_excluded(self):
        value = plan()
        value["recommendations"].append({"rank": 7, "dps_gain": 9, "upgrade_cost_gp": 1001})
        result = analyze_frontier(value)
        self.assertEqual(result["excluded_counts"]["over_budget"], 1)

    def test_duplicate_loadout_identity_is_rejected(self):
        value = plan()
        value["recommendations"].append(copy.deepcopy(value["recommendations"][0]))
        value["recommendations"][-1]["rank"] = 99
        with self.assertRaises(ValueError):
            analyze_frontier(value)

    def test_invalid_gain_and_cost_are_rejected(self):
        value = plan()
        value["recommendations"][0]["dps_gain"] = float("nan")
        with self.assertRaises(ValueError):
            analyze_frontier(value)
        value = plan()
        value["recommendations"][0]["upgrade_cost_gp"] = -1
        with self.assertRaises(ValueError):
            analyze_frontier(value)

    def test_empty_candidate_list_is_explicit(self):
        result = analyze_frontier({"recommendations": [], "upgrade_budget_gp": 100})
        self.assertEqual(result["status"], "no_positive_candidate")
        self.assertEqual(result["frontier_count"], 0)
        self.assertIsNone(result["best_dps_gain_candidate"])

    def test_malformed_plan_and_recommendations_are_rejected(self):
        with self.assertRaises(ValueError):
            analyze_frontier([])
        with self.assertRaises(ValueError):
            analyze_frontier({"recommendations": {}})


if __name__ == "__main__":
    unittest.main()
