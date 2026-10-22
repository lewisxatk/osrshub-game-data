"""Regression tests for conservative account quest progression."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from report_account_quest_progression import build_report

def quest(name, requirements, skills, req_state="known", skill_state="known", key=None):
    return {"key": key or name.casefold(), "name": name, "requirements": requirements, "skill_requirements": skills,
            "field_status": {"requirements": req_state, "skill_requirements": skill_state}, "source_url": "https://example.org"}

def profile(completed=(), skills=None):
    return {"label": "Fixture", "completed_quests": list(completed), "skills": skills or {}, "import_status": "validated", "errors": []}

class AccountQuestProgressionTests(unittest.TestCase):
    def test_ready_when_known_requirements_are_met(self):
        result = build_report([quest("A", [], [])], [], profile())
        self.assertEqual(result["counts"]["ready"], 1)

    def test_known_missing_prerequisite_blocks(self):
        result = build_report([quest("A", ["B"], [])], [], profile())
        self.assertEqual(result["quests"][0]["status"], "blocked")
        self.assertEqual(result["quests"][0]["blockers"][0]["name"], "B")

    def test_unknown_requirement_field_never_means_ready(self):
        result = build_report([quest("A", [], [], req_state="unknown")], [], profile())
        self.assertEqual(result["quests"][0]["status"], "unknown")

    def test_missing_account_skill_is_unknown(self):
        result = build_report([quest("A", [], [{"skill": "Crafting", "level": 20}])], [], profile())
        self.assertEqual(result["quests"][0]["status"], "unknown")

    def test_skill_below_requirement_blocks(self):
        result = build_report([quest("A", [], [{"skill": "Crafting", "level": 20}])], [], profile(skills={"Crafting": 15}))
        self.assertEqual(result["quests"][0]["status"], "blocked")

    def test_completed_profile_quest_is_preserved(self):
        result = build_report([quest("A", [], [], req_state="unknown", skill_state="unknown")], [], profile(["a"]))
        self.assertEqual(result["quests"][0]["status"], "completed")

    def test_malformed_root_fails(self):
        result = build_report({}, [], profile())
        self.assertEqual(result["status"], "failed")

if __name__ == "__main__":
    unittest.main()
