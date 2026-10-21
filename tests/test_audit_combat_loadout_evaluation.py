"""Tests for consistency audit of baseline loadout reports."""
import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from audit_combat_loadout_evaluation import audit_report

def sample():
 return {"status":"baseline_loadout_estimate_with_limitations","budget_gp":100,"total_cost_gp":70,"remaining_budget_gp":30,
 "selected_items":[{"item_id":1,"item_name":"Sword","slot":"weapon","cost_gp":50,"attack_bonus_contribution":10,"melee_strength_contribution":12},
                   {"item_id":2,"item_name":"Helm","slot":"head","cost_gp":20,"attack_bonus_contribution":3,"melee_strength_contribution":4}],
 "aggregated_bonuses":{"attack_style_bonus":13,"melee_strength":16},
 "weapon":{"item_id":1,"item_name":"Sword","attack_speed_ticks":4},
 "combat_result":{"status":"baseline_only","dps":2.1},
 "guardrails":["Not boss-specific"]}
class LoadoutEvaluationAuditTests(unittest.TestCase):
 def test_consistent_report_passes(self):
  self.assertEqual(audit_report(sample())["status"],"passed")
 def test_cost_sum_mismatch_fails(self):
  report=sample(); report["total_cost_gp"]=60
  self.assertEqual(audit_report(report)["status"],"failed")
 def test_budget_math_mismatch_fails(self):
  report=sample(); report["remaining_budget_gp"]=20
  self.assertTrue(any("remaining_budget" in e for e in audit_report(report)["errors"]))
 def test_aggregated_bonus_mismatch_fails(self):
  report=sample(); report["aggregated_bonuses"]["melee_strength"]=99
  self.assertTrue(any("melee_strength" in e for e in audit_report(report)["errors"]))
 def test_duplicate_slot_fails(self):
  report=sample(); report["selected_items"][1]["slot"]="weapon"
  self.assertEqual(audit_report(report)["status"],"failed")
 def test_invalid_dps_fails(self):
  report=sample(); report["combat_result"]["dps"]=-1
  self.assertEqual(audit_report(report)["status"],"failed")
if __name__=="__main__":unittest.main()
