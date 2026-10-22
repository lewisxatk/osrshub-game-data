import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from report_quest_reward_item_evidence import build_report


class QuestRewardItemEvidenceTests(unittest.TestCase):
    def test_exact_normalized_name_match_is_emitted_with_guardrails(self):
        quests = [{
            "key": "quest-a", "name": "Quest A", "rewards": [" Dragon scimitar "],
            "field_status": {"rewards": "known"}, "field_sources": {"rewards": "https://example.invalid/quest"}
        }]
        items = [{"id": 123, "name": "Dragon Scimitar", "sources": ["https://example.invalid/item"]}]
        report = build_report(quests, items)
        self.assertEqual(report["exact_reward_item_match_count"], 1)
        match = report["matches"][0]
        self.assertEqual(match["item_id"], 123)
        self.assertEqual(match["match_method"], "exact_case_insensitive_normalized_name")
        self.assertIn("does not establish", match["interpretation"])

    def test_no_fuzzy_match_or_ambiguous_item_name(self):
        quests = [{"key": "q", "name": "Q", "rewards": ["Dragon scimitar"], "field_status": {"rewards": "known"}}]
        items = [{"id": 1, "name": "Dragon scimitar"}, {"id": 2, "name": " Dragon  scimitar "}]
        report = build_report(quests, items)
        self.assertEqual(report["exact_reward_item_match_count"], 0)
        self.assertIn("ambiguous", report["unmatched_reward_text"][0]["reason"])

    def test_same_item_id_duplicate_is_not_marked_ambiguous(self):
        quests = [{"key": "q", "name": "Q", "rewards": ["Dragon scimitar"], "field_status": {"rewards": "known"}}]
        items = [{"id": 1, "name": "Dragon scimitar"}, {"id": 1, "name": " Dragon  scimitar "}]
        report = build_report(quests, items)
        self.assertEqual(report["exact_reward_item_match_count"], 1)

    def test_unknown_rewards_stay_unknown(self):
        report = build_report([{"key": "q", "name": "Q", "rewards": []}], [])
        self.assertEqual(report["quests_with_unknown_reward_fields"], 1)
        self.assertEqual(report["exact_reward_item_match_count"], 0)

    def test_empty_datasets_do_not_look_like_a_complete_success(self):
        report = build_report([], [])
        self.assertEqual(report["status"], "review_required")
        self.assertEqual(report["exact_reward_item_match_count"], 0)

    def test_dataset_shapes_are_validated(self):
        with self.assertRaises(ValueError):
            build_report({}, [])
        with self.assertRaises(ValueError):
            build_report([], [None])


if __name__ == "__main__":
    unittest.main()
