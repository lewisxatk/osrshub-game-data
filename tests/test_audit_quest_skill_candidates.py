"""Regression tests for the quest skill candidate audit."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_quest_skill_candidates import build_audit

SOURCE = "https://oldschool.runescape.wiki/w/Quests/Requirements_by_quest"


def candidate(key, name, skill, level, status="matched", matched_text=None):
    return {
        "quest_key": key,
        "quest_name": name,
        "skill": skill,
        "level": level,
        "matched_text": matched_text or f"{level} {skill}",
        "source_url": SOURCE,
        "catalogue_match_status": status,
        "candidate_status": "raw_text_candidate_needs_manual_review",
    }


def evidence(key, name, status="matched"):
    return {"quest_key": key, "quest_name": name, "source_url": SOURCE, "catalogue_match_status": status}


class QuestSkillCandidateAuditTests(unittest.TestCase):
    def test_counts_candidates_by_skill_and_flags_unmatched_titles(self):
        candidates = [
            candidate("1", "A", "Sailing", 30),
            candidate("unmatched-b", "B", "Magic", 40, "unmatched_catalogue_title"),
        ]
        report = build_audit(candidates, [
            evidence("1", "A"),
            evidence("unmatched-b", "B", "unmatched_catalogue_title"),
            evidence("3", "C"),
        ])
        self.assertEqual(report["candidate_counts_by_skill"], {"Magic": 1, "Sailing": 1})
        self.assertEqual(len(report["unmatched_catalogue_candidates"]), 1)
        self.assertEqual(report["evidence_quests_without_skill_candidates"], 1)
        self.assertEqual(report["errors"], [])

    def test_flags_repeated_quest_skill_matches_without_calling_them_facts(self):
        rows = [candidate("1", "A", "Mining", 20), candidate("1", "A", "Mining", 30)]
        report = build_audit(rows, [evidence("1", "A")])
        self.assertEqual(len(report["repeated_quest_skill_matches"]), 1)
        self.assertTrue(report["checks"]["does_not_promote_candidates_to_facts"])
        self.assertEqual(report["status"], "review_required")

    def test_malformed_candidate_is_reported(self):
        report = build_audit([{"quest_key": "1", "quest_name": "A", "skill": "Magic", "level": 100}], [])
        self.assertIn("missing_or_invalid_key_name_skill_level", {x["reason"] for x in report["errors"]})
        self.assertEqual(report["status"], "failed")


if __name__ == "__main__":
    unittest.main()
