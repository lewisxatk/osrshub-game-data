"""Regression tests for descriptive dataset coverage reporting."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import report_coverage


class CoverageReportTests(unittest.TestCase):
    def test_zero_is_a_present_value(self):
        summary = report_coverage.summarize_rows(
            [{"prayer": 0}, {"prayer": None}], ("prayer",)
        )
        self.assertEqual(summary["fields"]["prayer"]["records_with_value"], 1)
        self.assertEqual(summary["fields"]["prayer"]["coverage_percent"], 50.0)

    def test_empty_values_are_missing(self):
        summary = report_coverage.summarize_rows(
            [{"a": None}, {"a": ""}, {"a": []}, {"a": {}}], ("a",)
        )
        self.assertEqual(summary["fields"]["a"]["records_with_value"], 0)
        self.assertEqual(summary["fields"]["a"]["coverage_percent"], 0.0)

    def test_nested_nonempty_values_are_present(self):
        summary = report_coverage.summarize_rows(
            [{"equipment": {"slot": "weapon"}}, {"equipment": {}}], ("equipment",)
        )
        self.assertEqual(summary["fields"]["equipment"]["records_with_value"], 1)

    def test_non_object_rows_are_counted(self):
        summary = report_coverage.summarize_rows(
            [{"id": 1}, None, "bad-row"], ("id",)
        )
        self.assertEqual(summary["record_count"], 3)
        self.assertEqual(summary["non_object_record_count"], 2)
        self.assertEqual(summary["fields"]["id"]["records_with_value"], 1)

    def test_empty_dataset_has_zero_percent_coverage(self):
        summary = report_coverage.summarize_rows([], ("attack_speed",))
        self.assertEqual(summary["record_count"], 0)
        self.assertEqual(summary["fields"]["attack_speed"]["coverage_percent"], 0.0)

    def test_non_array_dataset_is_rejected(self):
        with self.assertRaises(ValueError):
            report_coverage.summarize_rows({"id": 1}, ("id",))


if __name__ == "__main__":
    unittest.main()
