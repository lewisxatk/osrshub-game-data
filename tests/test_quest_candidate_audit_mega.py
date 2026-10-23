"""Regression tests for the quest skill-candidate evidence audit."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_quest_skill_candidates import build_audit

SOURCE = "https://oldschool.runescape.wiki/w/Quests/Requirements_by_quest"


def evidence(key="1", name="Cook's Assistant", source=SOURCE, status="matched"):
    return [{"quest_key": key, "quest_name": name, "source_url": source, "catalogue_match_status": status}]


def candidate(key="1", name="Cook's Assistant", source=SOURCE, status="matched",
              review_status="raw_text_candidate_needs_manual_review", skill="Cooking", level=10,
              matched_text="10 Cooking"):
    return {"quest_key": key, "quest_name": name, "source_url": source,
            "catalogue_match_status": status, "candidate_status": review_status,
            "skill": skill, "level": level, "matched_text": matched_text}


class QuestSkillCandidateAuditTests(unittest.TestCase):
    def test_valid_candidate_remains_review_only(self):
        report = build_audit([candidate()], evidence())
        self.assertEqual(report["status"], "passed_with_review_limits")
        self.assertEqual(report["errors"], [])
        self.assertTrue(report["checks"]["does_not_promote_candidates_to_facts"])

    def test_unverified_candidate_status_fails(self):
        report = build_audit([candidate(review_status="verified")], evidence())
        self.assertEqual(report["status"], "failed")
        self.assertIn("candidate_not_explicitly_review_only", {x["reason"] for x in report["errors"]})

    def test_external_source_is_rejected(self):
        report = build_audit([candidate(source="https://example.com/fake")], evidence())
        self.assertIn("missing_or_untrusted_source_url", {x["reason"] for x in report["errors"]})

    def test_candidate_source_must_match_evidence(self):
        report = build_audit([candidate(source="https://oldschool.runescape.wiki/w/Other")], evidence())
        self.assertIn("candidate_source_does_not_match_evidence_source", {x["reason"] for x in report["errors"]})

    def test_matched_candidate_name_must_match_evidence(self):
        report = build_audit([candidate(name="Different quest")], evidence())
        self.assertIn("matched_candidate_name_disagrees_with_evidence", {x["reason"] for x in report["errors"]})

    def test_candidate_must_reference_evidence(self):
        report = build_audit([candidate(key="missing")], evidence())
        self.assertIn("candidate_has_no_matching_evidence_record", {x["reason"] for x in report["errors"]})

    def test_duplicate_evidence_keys_fail(self):
        report = build_audit([candidate()], evidence() + evidence())
        self.assertIn("duplicate_evidence_key", {x["reason"] for x in report["errors"]})

    def test_unmatched_title_is_review_queue_not_hard_failure(self):
        ev = evidence(key="unmatched-cake", name="Uncatalogued quest", status="unmatched_catalogue_title")
        report = build_audit([candidate(key="unmatched-cake", name="Uncatalogued quest", status="unmatched_catalogue_title")], ev)
        self.assertEqual(report["status"], "review_required")
        self.assertEqual(report["errors"], [])
        self.assertEqual(len(report["unmatched_catalogue_candidates"]), 1)

    def test_multiple_levels_for_same_quest_skill_need_review(self):
        rows = [candidate(level=10, matched_text="10 Cooking"), candidate(level=20, matched_text="20 Cooking")]
        report = build_audit(rows, evidence())
        self.assertEqual(report["status"], "review_required")
        self.assertEqual(report["repeated_quest_skill_matches"][0]["levels"], [10, 20])

    def test_invalid_candidate_shape_fails(self):
        report = build_audit([{"quest_key": "1", "skill": "Cooking", "level": True}], evidence())
        self.assertEqual(report["status"], "failed")
        self.assertIn("missing_or_invalid_key_name_skill_level", {x["reason"] for x in report["errors"]})

    def test_duplicate_candidate_records_fail(self):
        row = candidate()
        report = build_audit([row, dict(row)], evidence())
        self.assertEqual(report["status"], "failed")
        self.assertIn("duplicate_candidate_record", {x["reason"] for x in report["errors"]})

    def test_input_shapes_are_required(self):
        with self.assertRaisesRegex(ValueError, "candidate input"):
            build_audit({}, [])
        with self.assertRaisesRegex(ValueError, "evidence input"):
            build_audit([], {})


if __name__ == "__main__":
    unittest.main()
