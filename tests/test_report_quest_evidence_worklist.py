"""Regression tests for the field-level quest evidence worklist."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from report_quest_evidence_worklist import build_worklist


FIELDS = ("requirements", "skill_requirements", "rewards", "members", "difficulty", "quest_type")


def quest(key="1", name="Example Quest", states=None, sources=None, **extra):
    row = {
        "key": key,
        "name": name,
        "requirements": [],
        "skill_requirements": [],
        "rewards": [],
        "members": None,
        "difficulty": None,
        "quest_type": None,
        "field_status": states or {field: "unknown" for field in FIELDS},
        "field_sources": sources or {},
        "source_url": "https://oldschool.runescape.wiki/w/Example_Quest",
    }
    row.update(extra)
    return row


def evidence(key="1", name="Example Quest", links=None, text="30 Crafting"):
    return {
        "quest_key": key,
        "quest_name": name,
        "requirements_text": text,
        "requirement_links": links or [],
        "source_url": "https://oldschool.runescape.wiki/w/Quests/Requirements_by_quest",
        "evidence_status": "raw_source_extracted_needs_structured_review",
        "catalogue_match_status": "matched",
    }


class QuestEvidenceWorklistTests(unittest.TestCase):
    def test_unknown_quest_fields_create_field_level_tasks(self):
        result = build_worklist([quest()], [])
        self.assertEqual(result["status"], "review_required")
        self.assertTrue(any(task["task_id"] == "1:requirements:verify" for task in result["tasks"]))
        self.assertTrue(any(task["task_type"] == "collect_raw_requirement_evidence" for task in result["tasks"]))

    def test_raw_requirement_links_are_candidates_not_verified_facts(self):
        row = evidence(links=[{"title": "Another Quest", "url": "https://oldschool.runescape.wiki/w/Another_Quest"}])
        result = build_worklist([quest()], [row])
        task = next(task for task in result["tasks"] if task["task_type"] == "review_unverified_prerequisite_candidates")
        self.assertEqual(task["candidate_links"][0]["title"], "Another Quest")
        self.assertIn("candidates only", task["reason"])
        self.assertEqual(task["priority"], "critical")

    def test_known_empty_without_field_source_is_flagged(self):
        states = {field: "unknown" for field in FIELDS}
        states["requirements"] = "known"
        row = quest(states=states, requirements=[])
        result = build_worklist([row], [evidence()])
        task_types = [task["task_type"] for task in result["tasks"] if task["field"] == "requirements"]
        self.assertIn("add_field_level_source", task_types)
        self.assertIn("verify_known_empty_claim", task_types)

    def test_valid_field_source_removes_source_task_for_that_field(self):
        states = {field: "unknown" for field in FIELDS}
        states["requirements"] = "known"
        sources = {"requirements": "https://oldschool.runescape.wiki/w/Example_Quest"}
        result = build_worklist([quest(states=states, sources=sources)], [evidence()])
        self.assertFalse(any(task["task_id"] == "1:requirements:source" for task in result["tasks"]))

    def test_duplicate_raw_evidence_is_not_selected_automatically(self):
        result = build_worklist([quest()], [evidence(), evidence()])
        task = next(task for task in result["tasks"] if task["task_type"] == "resolve_ambiguous_raw_evidence")
        self.assertIn("2 raw evidence rows", task["reason"])

    def test_duplicate_quest_keys_are_reported(self):
        result = build_worklist([quest(), quest(name="Other Quest")], [])
        self.assertTrue(any(task["task_type"] == "resolve_duplicate_quest_key" for task in result["tasks"]))

    def test_bad_input_shape_fails_closed(self):
        with self.assertRaises(ValueError):
            build_worklist({}, [])

    def test_worklist_is_deterministically_sorted_by_priority_then_name(self):
        result = build_worklist([quest(key="b", name="Zulu"), quest(key="a", name="Alpha")], [])
        self.assertEqual(result["tasks"], sorted(result["tasks"], key=lambda task: (-task["priority_score"], str(task.get("quest_name") or "").casefold(), task["task_id"])))
        self.assertEqual(result["priority_counts"]["critical"], sum(task["priority"] == "critical" for task in result["tasks"]))


if __name__ == "__main__":
    unittest.main()
