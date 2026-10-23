"""Regression tests for evidence-aware Combat Studio upgrade readiness."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_combat_upgrade_readiness import audit_plan


def sample_plan():
    return {
        "status": "upgrade_recommendations_with_limitations",
        "upgrade_budget_gp": 1000,
        "search": {"truncated": False},
        "recommendations": [{
            "rank": 1, "dps_gain": 0.2, "upgrade_cost_gp": 500,
            "remaining_budget_gp": 500, "warnings": [],
            "selected_items": [{
                "item_id": 10, "item_name": "Example sword",
                "source_urls": ["https://example.org/item"],
                "skill_requirements_status": "known_empty"
            }]
        }]
    }


def sample_registry():
    return {"registry_status": "research_scaffold", "mechanics": [
        {"mechanic_id": "attack_roll", "verification_status": "unverified"},
        {"mechanic_id": "prayers", "verification_status": "unsupported"}
    ]}


class CombatUpgradeReadinessTests(unittest.TestCase):
    def test_unknown_mechanics_require_review_not_false_certification(self):
        result = audit_plan(sample_plan(), sample_registry())
        self.assertEqual(result["recommendations"][0]["readiness"], "review_required")
        self.assertEqual(result["mechanics_summary"]["unverified_or_in_review"], 1)
        self.assertEqual(result["mechanics_summary"]["unsupported"], 1)

    def test_non_positive_gain_is_blocked(self):
        plan = sample_plan()
        plan["recommendations"][0]["dps_gain"] = 0
        result = audit_plan(plan, {"registry_status": "research_scaffold", "mechanics": []})
        self.assertEqual(result["recommendations"][0]["readiness"], "blocked")
        self.assertTrue(result["recommendations"][0]["blockers"])

    def test_search_truncation_is_visible(self):
        plan = sample_plan()
        plan["search"]["truncated"] = True
        result = audit_plan(plan, {"registry_status": "research_scaffold", "mechanics": []})
        self.assertTrue(result["search_truncated"])
        self.assertTrue(any("truncated" in item for item in result["recommendations"][0]["review_items"]))

    def test_missing_item_source_and_requirement_status_are_review_flags(self):
        plan = sample_plan()
        item = plan["recommendations"][0]["selected_items"][0]
        item.pop("source_urls")
        item.pop("skill_requirements_status")
        result = audit_plan(plan, {"registry_status": "research_scaffold", "mechanics": []})
        self.assertTrue(any("source URL" in item for item in result["recommendations"][0]["review_items"]))
        self.assertTrue(any("requirement" in item for item in result["recommendations"][0]["review_items"]))

    def test_budget_arithmetic_mismatch_is_flagged(self):
        plan = sample_plan()
        plan["recommendations"][0]["remaining_budget_gp"] = 400
        result = audit_plan(plan, {"registry_status": "research_scaffold", "mechanics": []})
        self.assertTrue(any("do not reconcile" in item for item in result["recommendations"][0]["review_items"]))


if __name__ == "__main__":
    unittest.main()
