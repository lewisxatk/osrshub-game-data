"""Tests for the quest prerequisite graph."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_quest_relationships import build_graph


def quest(key, name, requirements=None):
    return {"key": key, "name": name, "requirements": requirements or [],
            "skill_requirements": [], "source_url": None}


class QuestRelationshipTests(unittest.TestCase):
    def test_builds_prerequisite_and_reverse_dependent_edges_case_insensitively(self):
        rows, report = build_graph([
            quest("a", "Cook's Assistant"),
            quest("b", "Recipe for Disaster", ["cook's assistant"]),
        ])
        child = next(row for row in rows if row["quest_key"] == "b")
        parent = next(row for row in rows if row["quest_key"] == "a")
        self.assertEqual(child["prerequisites"], [{"quest_key": "a", "name": "Cook's Assistant"}])
        self.assertEqual(parent["dependents"], [{"quest_key": "b", "name": "Recipe for Disaster"}])
        self.assertEqual(report["resolved_prerequisite_edges"], 1)

    def test_reports_unresolved_and_ambiguous_names(self):
        _, report = build_graph([
            quest("a", "Quest A", ["Missing quest", "Shared"]),
            quest("b", "Shared"), quest("c", "shared"),
        ])
        reasons = {row["reason"] for row in report["unresolved_requirements"]}
        self.assertEqual(reasons, {"not_found", "ambiguous_name"})

    def test_rejects_duplicate_keys(self):
        with self.assertRaisesRegex(ValueError, "duplicate quest key"):
            build_graph([quest("same", "Quest A"), quest("same", "Quest B")])

    def test_detects_cycles(self):
        _, report = build_graph([
            quest("a", "Quest A", ["Quest B"]),
            quest("b", "Quest B", ["Quest A"]),
        ])
        self.assertEqual(report["cycle_count"], 1)
        self.assertEqual(report["status"], "failed")

    def test_empty_dataset_is_a_valid_empty_graph(self):
        rows, report = build_graph([])
        self.assertEqual(rows, [])
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["quest_count"], 0)


if __name__ == "__main__":
    unittest.main()
