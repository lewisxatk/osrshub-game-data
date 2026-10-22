"""Tests for eligibility coverage summaries and conservative unknown handling."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from report_item_eligibility_coverage import summarize_eligibility


class ItemEligibilityCoverageTests(unittest.TestCase):
    def test_summarizes_statuses_gaps_and_provenance(self):
        report = {"results": [
            {"overall_status": "ineligible_by_known_skill_requirement", "reasons": ["Requires Attack 70 (player has 60)"], "requirement_sources": ["OSRS Wiki"], "requirement_source_urls": ["https://oldschool.runescape.wiki/w/A"], "manual_exclusion": False},
            {"overall_status": "unknown", "reasons": ["No normalized skill requirement record exists for this item"], "requirement_sources": [], "requirement_source_urls": [], "manual_exclusion": False},
            {"overall_status": "unknown", "reasons": ["Player profile is missing skill levels: Defence", "Quest, unlock, item-variant, and requirement-completeness checks are not fully verified"], "requirement_sources": ["Source"], "requirement_source_urls": [], "manual_exclusion": False},
            {"overall_status": "excluded", "reasons": ["Manually excluded by the player"], "requirement_sources": [], "requirement_source_urls": [], "manual_exclusion": True},
        ]}
        result = summarize_eligibility(report)
        self.assertEqual(result["status"], "passed_with_warnings")
        self.assertEqual(result["counts"]["unknown"], 2)
        self.assertEqual(result["counts"]["excluded"], 1)
        self.assertEqual(result["items_missing_requirement_record"], 1)
        self.assertEqual(result["items_missing_player_skill_levels"], 1)
        self.assertEqual(result["items_with_unverified_unlock_or_completeness_checks"], 1)
        self.assertEqual(result["items_with_https_requirement_source_urls"], 1)
        self.assertEqual(sum(result["counts"].values()), result["item_count_evaluated"])

    def test_never_creates_an_eligible_status(self):
        result = summarize_eligibility({"results": [{"overall_status": "unknown", "reasons": [], "requirement_sources": [], "requirement_source_urls": []}]})
        self.assertNotIn("eligible", result["counts"])
        self.assertTrue(any("not promoted to fully eligible" in x for x in result["guardrails"]))

    def test_malformed_result_is_reported_as_failed(self):
        result = summarize_eligibility({"results": [None, {"overall_status": "eligible"}]})
        self.assertEqual(result["status"], "failed")
        self.assertEqual(len(result["errors"]), 2)

    def test_rejects_wrong_root_or_results_type(self):
        with self.assertRaises(ValueError):
            summarize_eligibility([])
        with self.assertRaises(ValueError):
            summarize_eligibility({"results": {}})


if __name__ == "__main__":
    unittest.main()
