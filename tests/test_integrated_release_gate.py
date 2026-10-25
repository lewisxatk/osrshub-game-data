import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_integrated_release_gate import build_gate

class IntegratedReleaseGateTests(unittest.TestCase):
    def write(self, root, name, value):
        (root / name).write_text(json.dumps(value), encoding="utf-8")

    def test_missing_report_blocks_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = build_gate(root, {"census": "database-census.json"})
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["blocking_component_count"], 1)
            self.assertEqual(result["components"]["census"]["state"], "missing_or_invalid")

    def test_review_required_is_not_promoted_to_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "quest.json", {"status": "review_required", "warning_count": 0})
            result = build_gate(root, {"quest_evidence": "quest.json"})
            self.assertEqual(result["status"], "review_required")
            self.assertEqual(result["components"]["quest_evidence"]["state"], "review_required")

    def test_failed_component_blocks_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "integrity.json", {"status": "failed", "error_count": 2})
            result = build_gate(root, {"integrity": "integrity.json"})
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["error_count"], 1)

    def test_all_passed_components_can_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "a.json", {"status": "passed", "warning_count": 0})
            self.write(root, "b.json", {"status": "success", "warning_count": 0})
            result = build_gate(root, {"a": "a.json", "b": "b.json"})
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["component_count"], 2)

    def test_malformed_json_blocks_release(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bad.json").write_text("{nope", encoding="utf-8")
            result = build_gate(root, {"bad": "bad.json"})
            self.assertEqual(result["status"], "failed")
            self.assertIn("Unreadable report", result["errors"][0]["message"])

    def test_unknown_status_requires_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.write(root, "new.json", {"status": "not_yet_classified"})
            result = build_gate(root, {"new": "new.json"})
            self.assertEqual(result["status"], "review_required")

if __name__ == "__main__":
    unittest.main()
