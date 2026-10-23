import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from analyze_combat_ranking_sensitivity import analyze_sensitivity


def candidate(ids, average, worst, best, cost):
    return {
        "selected_item_ids": ids,
        "weighted_average_dps": average,
        "worst_case_dps": worst,
        "best_case_dps": best,
        "dps_spread": best - worst,
        "total_cost_gp": cost,
    }


class CombatRankingSensitivityTests(unittest.TestCase):
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
                candidate([3], 8.0, 7.0, 9.0, 500),
            ],
        }

    def test_detects_winner_change_between_average_and_worst_case(self):
        result = analyze_sensitivity(self.report, step_percent=50)
        self.assertEqual(result["profiles"][0]["winner_item_ids"], [1])
        self.assertEqual(result["profiles"][-1]["winner_item_ids"], [2])
        self.assertGreater(result["winner_change_count"], 1)

    def test_profile_count_includes_both_endpoints(self):
        result = analyze_sensitivity(self.report, step_percent=25)
        self.assertEqual(result["risk_profile_count"], 5)
        self.assertEqual(result["profiles"][0]["risk_aversion"], 0)
        self.assertEqual(result["profiles"][-1]["risk_aversion"], 1)

    def test_stability_shares_sum_to_one_when_candidates_exist(self):
        result = analyze_sensitivity(self.report, step_percent=10)
        self.assertAlmostEqual(sum(row["first_place_share"] for row in result["winner_stability"]), 1.0)
        self.assertEqual(sum(row["first_place_profiles"] for row in result["winner_stability"]), 11)

    def test_empty_candidate_report_is_valid_and_explicit(self):
        result = analyze_sensitivity({"ranked_candidates": []})
        self.assertEqual(result["source_candidate_count"], 0)
        self.assertTrue(all(profile["winner_item_ids"] is None for profile in result["profiles"]))
        self.assertEqual(result["winner_stability"], [])

    def test_rejects_duplicate_candidate_ids(self):
        report = {"ranked_candidates": [candidate([1], 10, 9, 11, 10), candidate([1], 8, 7, 9, 20)]}
        with self.assertRaisesRegex(ValueError, "duplicate candidate"):
            analyze_sensitivity(report)

    def test_rejects_bad_dps_range_and_nonfinite_values(self):
        bad = {"ranked_candidates": [candidate([1], 8, 9, 10, 10)]}
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            analyze_sensitivity(bad)
        bad = {"ranked_candidates": [candidate([1], float("nan"), 7, 9, 10)]}
        with self.assertRaisesRegex(ValueError, "finite"):
            analyze_sensitivity(bad)

    def test_rejects_invalid_sampling_and_top_n(self):
        for step in (0, 7, True):
            with self.subTest(step=step), self.assertRaisesRegex(ValueError, "step_percent"):
                analyze_sensitivity(self.report, step_percent=step)
        for top_n in (0, 21, True):
            with self.subTest(top_n=top_n), self.assertRaisesRegex(ValueError, "top_n"):
                analyze_sensitivity(self.report, top_n=top_n)


if __name__ == "__main__":
    unittest.main()
