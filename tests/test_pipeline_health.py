"""Tests for the consolidated pipeline health report."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import report_pipeline_health as health


class PipelineHealthTests(unittest.TestCase):
    def test_all_present_and_passed_reports_pass(self):
        reports = {
            "validation": ({"status": "passed"}, None),
            "schema": ({"status": "passed"}, None),
        }
        result = health.summarize_reports(reports)
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["missing_reports"], [])

    def test_missing_report_marks_pipeline_incomplete(self):
        result = health.summarize_reports({
            "validation": ({"status": "passed"}, None),
            "coverage": (None, "missing"),
        })
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["missing_reports"], ["coverage"])

    def test_failed_report_takes_precedence_over_missing(self):
        result = health.summarize_reports({
            "validation": ({"status": "failed"}, None),
            "coverage": (None, "missing"),
        })
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_reports"], ["validation"])


if __name__ == "__main__":
    unittest.main()
