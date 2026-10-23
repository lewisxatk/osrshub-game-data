"""Tests for the source/fixture-aware combat mechanics readiness report."""
import json
import sys
import unittest
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from report_combat_mechanics_readiness import build_report

class CombatMechanicsReadinessTests(unittest.TestCase):
    def setUp(self):
        self.registry = {"registry_status":"research_scaffold","mechanics":[
          {"mechanic_id":"attack_roll","label":"Attack roll","domain":"accuracy","implementation_status":"implemented_scoped","verification_status":"unverified","scope":"caller-supplied inputs","source_references":[],"regression_fixtures":[],"limitations":["Not independently verified"]},
          {"mechanic_id":"prayers","label":"Prayers","domain":"boosts","implementation_status":"not_implemented","verification_status":"unsupported","scope":"No modifier","source_references":[],"regression_fixtures":[],"limitations":["Not modelled"]}]}
    def test_reports_gaps_without_promoting_status(self):
        report = build_report(self.registry)
        self.assertEqual(report["status"], "review_required")
        self.assertEqual(report["verified_percent"], 0.0)
        self.assertEqual(report["verification_counts"]["unverified"], 1)
        self.assertEqual(report["verification_counts"]["unsupported"], 1)
        self.assertEqual(len(report["verification_gaps"]), 2)
        self.assertEqual(self.registry["mechanics"][0]["verification_status"], "unverified")
    def test_verified_record_with_evidence_is_not_a_gap(self):
        registry = json.loads(json.dumps(self.registry))
        row = registry["mechanics"][0]
        row["verification_status"] = "verified"
        row["source_references"] = [{"url":"https://oldschool.runescape.wiki/w/Attack","title":"Attack","accessed_at":"2026-10-23","claim":"Defines scoped attack-roll inputs"}]
        row["regression_fixtures"] = ["tests/test_combat_math.py::test_attack_roll"]
        report = build_report(registry)
        self.assertEqual(report["verified_percent"], 50.0)
        self.assertNotIn("attack_roll", [gap["mechanic_id"] for gap in report["verification_gaps"]])
    def test_duplicate_ids_are_reported_as_failed(self):
        registry = json.loads(json.dumps(self.registry))
        registry["mechanics"].append(json.loads(json.dumps(registry["mechanics"][0])))
        report = build_report(registry)
        self.assertEqual(report["status"], "failed")
        self.assertTrue(any("duplicate mechanic_id" in error for error in report["errors"]))
    def test_empty_registry_has_zero_percentages(self):
        report = build_report({"registry_status":"research_scaffold","mechanics":[]})
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["verified_percent"], 0.0)
        self.assertEqual(report["implemented_scoped_percent"], 0.0)
    def test_invalid_mechanics_container_raises(self):
        with self.assertRaises(ValueError):
            build_report({"mechanics":None})

if __name__ == "__main__":
    unittest.main()
