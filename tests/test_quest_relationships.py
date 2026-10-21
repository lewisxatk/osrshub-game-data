"""Tests for the quest prerequisite graph."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_quest_relationships import build_graph, find_cycles

def quest(key, name, requirements=None):
    return {"key": key, "name": name, "requirements": requirements or [],
            "skill_requirements": [], "source_url": None}

class QuestRelationshipTests(unittest.TestCase):
    def test_builds_prerequisite_and_reverse_dependent_edges(self):
        rows, report = build_graph([quest("a", "Cook's Assistant"), quest("b", "Recipe for Disaster", ["cook's assistant"])])
        child = next(row for row in rows if row["quest_key"] == "b")
        parent = next(row for row in rows if row["quest_key"] == "a")
        self.assertEqual(child["prerequisites"], [{"quest_key":"a","name":"Cook's Assistant","completion_state":"completed"}])
        self.assertEqual(parent["dependents"], [{"quest_key":"b","name":"Recipe for Disaster"}])
        self.assertEqual(report["resolved_prerequisite_edges"], 1)

    def test_reports_unresolved_and_ambiguous_names(self):
        _, report = build_graph([quest("a","Quest A",["Missing quest","Shared"]),quest("b","Shared"),quest("c","shared")])
        self.assertEqual({row["reason"] for row in report["unresolved_requirements"]},{"not_found","ambiguous_name"})

    def test_started_prefix_is_preserved(self):
        rows, report = build_graph([quest("a","Restless Ghost"),quest("b","Example Quest",["Started: Restless Ghost"])])
        child = next(row for row in rows if row["quest_key"] == "b")
        self.assertEqual(child["prerequisites"], [{"quest_key":"a","name":"Restless Ghost","completion_state":"started"}])
        self.assertEqual(report["unresolved_requirement_count"], 0)

    def test_malformed_requirement_list_is_visible_on_record_and_report(self):
        rows, report = build_graph([{"key":"a","name":"Quest A","requirements":"Quest B"},quest("b","Quest B")])
        row = next(item for item in rows if item["quest_key"] == "a")
        self.assertEqual(row["prerequisites"], [])
        self.assertEqual(row["unresolved_requirements"], ["'Quest B'"])
        self.assertEqual(report["unresolved_requirements"][0]["reason"], "malformed_requirement_list")

    def test_invalid_requirement_entries_are_reported(self):
        rows, report = build_graph([{"key":"a","name":"Quest A","requirements":[None," "]}])
        self.assertEqual(rows[0]["unresolved_requirements"], [" ","None"])
        self.assertEqual(report["unresolved_requirement_count"], 2)

    def test_rejects_duplicate_keys(self):
        with self.assertRaisesRegex(ValueError,"duplicate quest key"):
            build_graph([quest("same","Quest A"),quest("same","Quest B")])

    def test_detects_cycles(self):
        _, report = build_graph([quest("a","Quest A",["Quest B"]),quest("b","Quest B",["Quest A"])])
        self.assertEqual(report["cycle_count"], 1)
        self.assertEqual(report["status"], "failed")

    def test_long_dependency_chain_does_not_recurse(self):
        graph = {}
        total = 1500
        for i in range(total):
            graph[str(i)] = {"prerequisites": [{"quest_key": str(i-1)}] if i else []}
        self.assertEqual(find_cycles(graph), [])

    def test_empty_dataset_is_valid_empty_graph(self):
        rows, report = build_graph([])
        self.assertEqual(rows, [])
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["quest_count"], 0)

if __name__ == "__main__":
    unittest.main()
