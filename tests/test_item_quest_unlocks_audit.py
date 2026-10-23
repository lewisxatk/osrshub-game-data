"""Regression tests for the item-to-quest unlock evidence audit."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from audit_item_quest_unlocks import audit_item_quest_unlocks


def record(item_id=1, status="known_empty", quests=None, source="https://oldschool.runescape.wiki/"):
    return {"item_id": item_id, "requirements_status": status,
            "required_quests": [] if quests is None else quests, "source_url": source}


class ItemQuestUnlockAuditTests(unittest.TestCase):
    def test_source_backed_known_empty_record_can_pass(self):
        result = audit_item_quest_unlocks([record()])
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["knowledge_counts"]["known_empty"], 1)
        self.assertEqual(result["source_url_coverage_percent"], 100.0)

    def test_known_requires_at_least_one_quest(self):
        result = audit_item_quest_unlocks([record(status="known")])
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("use known_empty" in issue for issue in result["errors"]))

    def test_known_empty_cannot_list_quests(self):
        result = audit_item_quest_unlocks([record(status="known_empty", quests=["Example Quest"])])
        self.assertEqual(result["status"], "failed")
        self.assertTrue(any("known_empty" in issue for issue in result["errors"]))

    def test_unknown_with_quests_is_contradictory(self):
        result = audit_item_quest_unlocks([record(status="unknown", quests=["Example Quest"])])
        self.assertEqual(result["status"], "failed")

    def test_duplicate_item_ids_fail(self):
        result = audit_item_quest_unlocks([record(), record()])
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["duplicate_item_ids"], [1])

    def test_placeholder_sources_require_review(self):
        result = audit_item_quest_unlocks([record(source="https://example.test/item")])
        self.assertEqual(result["status"], "review_required")
        self.assertTrue(any("fixtures, not production evidence" in warning for warning in result["warnings"]))

    def test_missing_source_is_a_warning_not_an_invented_fact(self):
        result = audit_item_quest_unlocks([record(source=None)])
        self.assertEqual(result["status"], "review_required")
        self.assertEqual(result["source_url_coverage_percent"], 0.0)

    def test_missing_dataset_is_not_treated_as_empty_requirements(self):
        result = audit_item_quest_unlocks([])
        self.assertEqual(result["status"], "review_required")
        self.assertIn("unknown", " ".join(result["warnings"]).lower())


if __name__ == "__main__":
    unittest.main()
