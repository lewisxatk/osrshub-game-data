import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from rank_combat_scenario_robustness import rank_report


def candidate(ids, average, worst, best, cost):
    return {
        "selected_item_ids": ids,
        "weighted_average_dps": average,
        "worst_case_dps": worst,
        "best_case_dps": best,
        "dps_spread": best - worst,
        "total_cost_gp": cost,
        "scenario_results": [],
    }


class CombatScenarioRobustnessTests(unittest.TestCase):
    def setUp(self):
        self.report = {
            "schema_version": "1.0.0",
            "status": "scenario_ranked_candidates",
            "attack_style": "slash",
            "budget_gp": 5000,
            "scenario_count": 2,
            "ranked_candidates": [
                candidate([1], 10.0, 4.0, 16.0, 1000),
                candidate([2], 9.0, 8.0, 10.0, 1500),
            ],
        }

    def test_zero_risk_aversion_preserves_average_performance_order(self):
        result = rank_report(self.report, risk_aversion=0)
        self.assertEqual(result["ranked_candidates"][0]["selected_item_ids"], [1])
        self.assertEqual(result["ranked_candidates"][0]["risk_adjusted_dps"], 10.0)

    def test_full_risk_aversion_prioritizes_worst_case(self):
        result = rank_report(self.report, risk_aversion=1)
        self.assertEqual(result["ranked_candidates"][0]["selected_item_ids"], [2])
        self.assertEqual(result["ranked_candidates"][0]["risk_adjusted_dps"], 8.0)

    def test_intermediate_risk_aversion_is_explicit_weighted_tradeoff(self):
        result = rank_report(self.report, risk_aversion=0.5)
        scores = {tuple(row["selected_item_ids"]): row["risk_adjusted_dps"] for row in result["ranked_candidates"]}
        self.assertEqual(scores[(1,)], 7.0)
        self.assertEqual(scores[(2,)], 8.5)

    def test_rejects_invalid_risk_aversion(self):
        for value in (-0.1, 1.1, True, float("nan"), float("inf")):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError, "risk_aversion"):
                    rank_report(self.report, risk_aversion=value)

    def test_rejects_inconsistent_metrics(self):
        report = {"ranked_candidates": [candidate([1], 10, 9, 11, 100)]}
        report["ranked_candidates"][0]["dps_spread"] = 1
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            rank_report(report)

    def test_rejects_missing_metrics_and_boolean_ids(self):
        with self.assertRaisesRegex(ValueError, "missing fields"):
            rank_report({"ranked_candidates": [{"selected_item_ids": []}]})
        bad = {"ranked_candidates": [candidate([True], 10, 9, 11, 100)]}
        with self.assertRaisesRegex(ValueError, "selected_item_ids"):
            rank_report(bad)

    def test_respects_top_n_and_explains_bounded_search(self):
        result = rank_report(self.report, top_n=1)
        self.assertEqual(len(result["ranked_candidates"]), 1)
        self.assertTrue(any("bounded" in note for note in result["guardrails"]))


if __name__ == "__main__":
    unittest.main()
