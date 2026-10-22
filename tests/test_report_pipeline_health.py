"""Tests for pipeline-health aggregation."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from report_pipeline_health import summarize_reports

class PipelineHealthTests(unittest.TestCase):
    def test_successful_equipment_shortlist_is_included(self):
        result = summarize_reports({
            "equipment_shortlist": ({"status": "candidate_shortlist_only"}, None),
            "schema_validation": ({"status": "passed"}, None),
        })
        self.assertEqual(result["status"], "passed")
        self.assertEqual(result["checks"]["equipment_shortlist"]["status"], "candidate_shortlist_only")

    def test_missing_report_makes_health_incomplete(self):
        result = summarize_reports({"quest_facts": (None, "missing")})
        self.assertEqual(result["status"], "incomplete")
        self.assertEqual(result["missing_reports"], ["quest_facts"])

    def test_failed_report_takes_precedence_over_missing(self):
        result = summarize_reports({"missing": (None, "missing"), "bad": ({"status": "failed"}, None)})
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["failed_reports"], ["bad"])

    def test_unreadable_report_is_a_failure(self):
        result = summarize_reports({"bad_json": (None, "unreadable: invalid JSON")})
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["checks"]["bad_json"]["status"], "unreadable")


    def test_domain_consistency_failure_is_reported(self):
        result = summarize_reports({'domain_consistency': ({'status': 'failed'}, None)})
        self.assertEqual(result['status'], 'failed')
        self.assertIn('domain_consistency', result['failed_reports'])

    def test_domain_consistency_review_status_is_preserved(self):
        result = summarize_reports({'domain_consistency': ({'status': 'review_required'}, None)})
        self.assertEqual(result['checks']['domain_consistency']['status'], 'review_required')
        self.assertEqual(result['status'], 'review_required')
        self.assertEqual(result['review_required_reports'], ['domain_consistency'])

    def test_review_required_takes_precedence_over_missing_reports(self):
        result = summarize_reports({
            'missing': (None, 'missing'),
            'coverage': ({'status': 'review_required'}, None),
        })
        self.assertEqual(result['status'], 'review_required')
        self.assertEqual(result['missing_reports'], ['missing'])

    def test_non_object_json_payload_is_a_failure(self):
        result = summarize_reports({'bad_shape': (['not', 'an', 'object'], None)})
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['checks']['bad_shape']['status'], 'invalid_report')
        self.assertEqual(result['failed_reports'], ['bad_shape'])

    def test_unknown_status_is_preserved_without_fabricating_a_failure(self):
        result = summarize_reports({'future_report': ({'status': 'candidate_only'}, None)})
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['checks']['future_report']['status'], 'candidate_only')

if __name__ == "__main__":
    unittest.main()
