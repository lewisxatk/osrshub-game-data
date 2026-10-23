"""Regression tests for source-domain readiness inventory."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from report_extended_domain_readiness import build_report, collect_paths, summarize_domain


class ExtendedDomainReadinessTests(unittest.TestCase):
    def test_nested_paths_are_counted_without_array_indices(self):
        counts = collect_paths({"drops": [{"item_id": 42, "quantity": 3}, {"item_id": 99}]})
        self.assertEqual(counts["drops"], 1)
        self.assertEqual(counts["drops[].item_id"], 2)
        self.assertEqual(counts["drops[].quantity"], 1)

    def test_field_coverage_distinguishes_absent_and_empty(self):
        rows = [
            {"source_key": "a", "source_snapshot_url": "https://example.test/a", "value": 0, "empty": []},
            {"source_key": "b", "source_snapshot_url": "https://example.test/a", "value": None},
        ]
        result = summarize_domain(rows, "fixture.json")
        self.assertEqual(result["field_coverage"]["value"]["records_with_value"], 1)
        self.assertEqual(result["field_coverage"]["value"]["coverage_percent"], 50.0)
        self.assertNotIn("empty", result["field_coverage"])

    def test_duplicate_keys_and_missing_provenance_are_flagged(self):
        rows = [
            {"source_key": "same", "source_snapshot_url": "https://example.test/a"},
            {"source_key": "same", "source_snapshot_url": ""},
        ]
        result = summarize_domain(rows, "fixture.json")
        self.assertEqual(result["duplicate_source_keys"], ["same"])
        self.assertEqual(result["missing_source_url_count"], 1)

    def test_build_report_requires_all_configured_domains(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)
            (path / "prayers.json").write_text(json.dumps([
                {"source_key": "1", "source_snapshot_url": "https://example.test/prayers", "id": 1}
            ]), encoding="utf-8")
            result = build_report(path)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["domain_count"], 1)
            self.assertTrue(any("npc-drops.json" in error for error in result["errors"]))


if __name__ == "__main__":
    unittest.main()
