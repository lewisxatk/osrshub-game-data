"""Regression tests for the quest skill candidate audit."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_quest_skill_candidates import build_audit


class QuestSkillCandidateAuditTests(unittest.TestCase):
    def test_counts_candidates_by_skill_and_flags_unmatched_titles(self):
        candidates = [
            {"quest_key": "1", "quest_name": "A", "skill": "Sailing", "level": 30, "catalogue_match_status": "matched", "candidate_status": "raw_text_candidate_needs_manual_review"},
            {"quest_key": "unmatched-b", "quest_name": "B", "skill": "Magic", "level": 40, "catalogue_match_status": "unmatched_catalogue_title", "candidate_status": "raw_text_candidate_needs_manual_review"},
        ]
        report = build_audit(candidates, [{"quest_key": "1"}, {"quest_key": "unmatched-b"}, {"quest_key": "3"}])
        self.assertEqual(report["candidate_counts_by_skill"], {"Magic": 1, "Sailing": 1})
        self.assertEqual(len(report["unmatched_catalogue_candidates"]), 1)
        self.assertEqual(report["evidence_quests_without_skill_candidates"], 1)

    def test_flags_repeated_quest_skill_matches_without_calling_them_facts(self):
        candidate = {"quest_key": "1", "quest_name": "A", "skill": "Mining", "level": 20, "catalogue_match_status": "matched", "candidate_status": "raw_text_candidate_needs_manual_review"}
        report = build_audit([candidate, {**candidate, "level": 30}], [{"quest_key": "1"}])
        self.assertEqual(len(report["repeated_quest_skill_matches"]), 1)
        self.assertTrue(report["checks"]["does_not_promote_candidates_to_facts"])

    def test_malformed_candidate_is_reported(self):
        report = build_audit([{"quest_key": "1", "skill": "Magic", "level": 100}], [])
        self.assertEqual(len(report["malformed_candidates"]), 1)


if __name__ == "__main__":
    unittest.main()
