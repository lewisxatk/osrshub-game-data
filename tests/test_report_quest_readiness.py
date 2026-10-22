"""Tests for conservative quest-data readiness reporting."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import report_quest_readiness as readiness


class QuestReadinessTests(unittest.TestCase):
    def test_empty_data_is_incomplete_not_ready(self):
        result = readiness.build_report([], [], {"status": "missing_source"}, {"unresolved_requirement_count": 0})
        self.assertEqual(result["status"], "incomplete")
        self.assertFalse(result["account_restriction_safe_to_assume_unlisted_quests_complete"])
        self.assertTrue(result["warnings"])

    def test_unresolved_prerequisites_block_ready_status(self):
        quests = [{"name": "A", "source_url": "https://example.com", "requirements": ["Unknown"]}]
        rels = [{"name": "A"}]
        result = readiness.build_report(quests, rels, {"status": "passed"}, {"unresolved_requirement_count": 1})
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["unresolved_requirement_count"], 1)

    def test_field_coverage_is_measured_not_guessed(self):
        quests = [
            {"name": "A", "source_url": "https://example.com", "requirements": ["B"], "skill_requirements": [], "rewards": []},
            {"name": "B", "source_url": None, "requirements": [], "skill_requirements": [{"skill": "Attack", "level": 10}], "rewards": ["Reward"]},
        ]
        result = readiness.build_report(quests, [{}, {}], {"status": "passed"}, {"unresolved_requirement_count": 0})
        self.assertEqual(result["source_url_coverage_percent"], 50.0)
        self.assertEqual(result["prerequisite_coverage_percent"], 50.0)
        self.assertEqual(result["skill_requirement_coverage_percent"], 50.0)
        self.assertEqual(result["reward_coverage_percent"], 50.0)
        self.assertEqual(result["status"], "incomplete")

    def test_explicit_known_empty_is_not_counted_as_unknown(self):
        fields = ("requirements", "skill_requirements", "rewards", "members", "difficulty", "quest_type")
        states = {field: "unknown" for field in fields}
        states["requirements"] = "known"
        quest = {"name": "A", "requirements": [], "skill_requirements": [], "rewards": [], "field_status": states}
        result = readiness.build_report([quest], [], {"status": "passed"}, {"unresolved_requirement_count": 0})
        self.assertEqual(result["field_status_counts"]["requirements"]["known"], 1)
        self.assertEqual(result["field_status_counts"]["requirements"]["known_empty"], 1)
        self.assertEqual(result["field_status_counts"]["rewards"]["unknown"], 1)

    def test_invalid_record_is_reported(self):
        result = readiness.build_report([{"name": " " }], [], {}, {})
        self.assertEqual(result["status"], "failed")
        self.assertTrue(result["errors"])


if __name__ == "__main__":
    unittest.main()
