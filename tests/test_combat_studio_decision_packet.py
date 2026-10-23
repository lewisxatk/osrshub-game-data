"""Regression tests for the integrated Combat Studio decision packet."""
import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_combat_studio_decision_packet import build_decision_packet


def fixture():
    plan = {
        "status": "upgrade_recommendations_with_limitations",
        "attack_style": "slash",
        "upgrade_budget_gp": 1000,
        "baseline": {"item_ids": [10], "dps": 5.0, "weapon": "Example weapon"},
        "search": {"truncated": False},
        "warnings": ["Illustrative caller-provided inputs."],
        "recommendations": [{
            "rank": 1, "baseline_dps": 5.0, "candidate_dps": 6.0,
            "dps_gain": 1.0, "dps_gain_percent": 20.0,
            "upgrade_cost_gp": 500, "remaining_budget_gp": 500,
            "dps_gain_per_million_gp": 2000.0, "weapon": "Example weapon",
            "slot_changes": [{"slot": "weapon", "from_item_id": 10, "from_item_name": "Old",
                              "to_item_id": 11, "to_item_name": "New", "upgrade_cost_gp": 500,
                              "attack_bonus_delta": 2, "melee_strength_delta": 1}],
            "selected_items": [{"item_id": 11, "item_name": "New", "slot": "weapon", "cost_gp": 500}],
            "warnings": []
        }]
    }
    readiness = {
        "recommendation_counts": {"candidate_only": 0, "review_required": 1, "blocked": 0},
        "search_truncated": False,
        "warnings": ["Mechanics not independently verified."],
        "recommendations": [{"rank": 1, "readiness": "review_required", "blockers": [],
                             "review_items": ["Source review required."]}]
    }
    mechanics = {
        "mechanics_registry_status": "research_scaffold",
        "mechanics_summary": {"total": 8, "verified": 0, "unverified_or_in_review": 4, "unsupported": 4},
        "verified_percent": 0.0
    }
    sensitivity = {
        "source_candidate_count": 2, "risk_profile_count": 11,
        "winner_change_count": 2,
        "profiles": [{"risk_aversion": 0.0}, {"risk_aversion": 1.0}],
        "winner_stability": [
            {"selected_item_ids": [11], "first_place_profiles": 8, "profile_count": 11, "first_place_share": 0.7273},
            {"selected_item_ids": [12], "first_place_profiles": 3, "profile_count": 11, "first_place_share": 0.2727}
        ]
    }
    return plan, readiness, mechanics, sensitivity


class CombatStudioDecisionPacketTests(unittest.TestCase):
    def setUp(self):
        self.inputs = fixture()

    def test_integrates_top_candidate_and_account_scope(self):
        packet = build_decision_packet(*self.inputs)
        self.assertEqual(packet["status"], "review_required")
        self.assertEqual(packet["decision_scope"]["attack_style"], "slash")
        self.assertEqual(packet["decision_scope"]["budget_gp"], 1000)
        self.assertEqual(packet["top_candidate"]["dps_gain"], 1.0)
        self.assertEqual(packet["top_candidate"]["slot_changes"][0]["slot"], "weapon")

    def test_unverified_and_unsupported_mechanics_are_high_priority_actions(self):
        packet = build_decision_packet(*self.inputs)
        self.assertEqual(packet["action_queue"][0]["priority"], "P0")
        ids = {row["action_id"] for row in packet["action_queue"]}
        self.assertIn("verify_combat_mechanics", ids)
        self.assertIn("implement_supported_mechanics", ids)

    def test_risk_share_is_described_as_preference_sample_not_probability(self):
        packet = build_decision_packet(*self.inputs)
        self.assertEqual(packet["risk_sensitivity"]["most_frequent_winner"], [11])
        self.assertAlmostEqual(packet["risk_sensitivity"]["most_frequent_winner_share_of_sampled_preferences"], 0.7273)
        self.assertIn("not a probability", packet["risk_sensitivity"]["interpretation"])

    def test_truncated_search_adds_review_action(self):
        self.inputs[0]["search"]["truncated"] = True
        packet = build_decision_packet(*self.inputs)
        self.assertTrue(packet["decision_scope"]["search_truncated"])
        self.assertIn("expand_candidate_search", {row["action_id"] for row in packet["action_queue"]})
        self.assertEqual(next(g for g in packet["gates"] if g["gate"] == "search_completeness")["status"], "review_required")

    def test_no_candidate_is_not_misreported_as_proof_no_upgrade_exists(self):
        self.inputs[0]["recommendations"] = []
        packet = build_decision_packet(*self.inputs)
        self.assertEqual(packet["status"], "no_candidate")
        self.assertIsNone(packet["top_candidate"])
        self.assertIn("inspect_no_candidate_result", {row["action_id"] for row in packet["action_queue"]})
        self.assertTrue(any("does not prove no upgrade exists" in g["detail"] for g in packet["gates"]))

    def test_all_verified_no_warnings_still_remains_candidate_only_not_accuracy_claim(self):
        plan, readiness, mechanics, sensitivity = copy.deepcopy(self.inputs)
        readiness["recommendation_counts"] = {"candidate_only": 1, "review_required": 0, "blocked": 0}
        readiness["recommendations"][0]["readiness"] = "candidate_only"
        readiness["recommendations"][0]["review_items"] = []
        readiness["warnings"] = []
        mechanics["mechanics_summary"] = {"total": 1, "verified": 1, "unverified_or_in_review": 0, "unsupported": 0}
        mechanics["verified_percent"] = 100.0
        sensitivity["winner_change_count"] = 1
        plan["warnings"] = []
        plan["search"]["truncated"] = False
        packet = build_decision_packet(plan, readiness, mechanics, sensitivity)
        self.assertEqual(packet["status"], "candidate_only")
        self.assertTrue(any("not proof of game accuracy" in w for w in packet["warnings"]))

    def test_duplicate_or_malformed_root_inputs_are_rejected(self):
        with self.assertRaises(ValueError):
            build_decision_packet([], self.inputs[1], self.inputs[2], self.inputs[3])
        bad = copy.deepcopy(self.inputs[0])
        bad["recommendations"] = {}
        with self.assertRaises(ValueError):
            build_decision_packet(bad, *self.inputs[1:])

    def test_missing_sensitivity_profiles_are_review_required(self):
        self.inputs[3]["profiles"] = []
        self.inputs[3]["winner_stability"] = []
        packet = build_decision_packet(*self.inputs)
        self.assertEqual(next(g for g in packet["gates"] if g["gate"] == "risk_preference_sensitivity")["status"], "review_required")
        self.assertIn("review_risk_tradeoffs", {row["action_id"] for row in packet["action_queue"]} if packet["risk_sensitivity"]["winner_change_count"] > 1 else {row["action_id"] for row in packet["action_queue"]} | {"review_risk_tradeoffs"})

    def test_action_queue_is_priority_ordered(self):
        packet = build_decision_packet(*self.inputs)
        ranks = {"P0": 0, "P1": 1, "P2": 2}
        priorities = [ranks[row["priority"]] for row in packet["action_queue"]]
        self.assertEqual(priorities, sorted(priorities))


if __name__ == "__main__":
    unittest.main()
