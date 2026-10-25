import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_domain_graph_health import build_report

class DomainGraphHealthTests(unittest.TestCase):
    def sample(self):
        return {
            "items": [{"id": 1}, {"id": 2}, {"id": 3}],
            "equipment": [{"id": 1}],
            "weapons": [{"id": 1}, {"id": 3}],
            "requirements": [{"item_id": 1}, {"item_id": 2}],
            "combat_profiles": [{"id": 1}, {"id": 99}],
            "item_relationships": [{"item_id": 1}, {"item_id": 2}],
            "quests": [{"key": "quest-a"}, {"key": "quest-b"}],
            "quest_relationships": [{"quest_key": "quest-a"}],
            "monsters": [{"id": 10}],
        }
    def test_reports_missing_and_orphan_edges(self):
        report = build_report(self.sample())
        self.assertEqual(report["status"], "review_required")
        edges = {edge["edge_type"]: edge for edge in report["edges"]}
        self.assertEqual(edges["item_has_equipment_stats"]["source_without_target_count"], 2)
        self.assertEqual(edges["item_has_combat_profile"]["orphan_target_count"], 1)
        self.assertEqual(edges["quest_has_prerequisite_record"]["source_without_target_count"], 1)
    def test_does_not_claim_missing_datasets_are_zero_coverage(self):
        data = self.sample()
        del data["quests"]
        report = build_report(data)
        gap = next(g for g in report["gaps"] if g["edge_type"] == "quest_has_prerequisite_record")
        self.assertEqual(gap["state"], "not_assessed")
    def test_duplicate_and_missing_ids_are_reported(self):
        data = self.sample()
        data["items"].append({"id": 1})
        data["items"].append({"name": "no id"})
        report = build_report(data)
        self.assertGreaterEqual(report["integrity_issue_count"], 1)
        self.assertEqual(report["datasets"]["items"]["duplicate_id_count"], 1)
        self.assertEqual(report["datasets"]["items"]["missing_id_count"], 1)
    def test_empty_datasets_do_not_divide_by_zero(self):
        data = {name: [] for name in self.sample()}
        report = build_report(data)
        self.assertEqual(report["edges"][0]["source_coverage_percent"], 0.0)
    def test_input_errors_are_blocking(self):
        report = build_report(self.sample(), ["bad input"])
        self.assertEqual(report["status"], "failed")
if __name__ == "__main__":
    unittest.main()
