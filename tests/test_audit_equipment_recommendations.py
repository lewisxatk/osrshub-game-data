"""Regression tests for recommendation consistency and uncertainty guardrails."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_equipment_recommendations import audit

class EquipmentRecommendationAuditTests(unittest.TestCase):
    def setUp(self):
        self.shortlist = {"results_by_slot": {
            "head": [{"item_id":1,"item_name":"Helm","status":"candidate_with_unknown_restrictions","cost":100,"objective_value":5,"reasons":["Quest/unlock restrictions are not verified"]}],
            "body": [{"item_id":2,"item_name":"Body","status":"unknown","cost":None,"objective_value":None,"reasons":["No valid cost"]}]
        }}
        self.loadout = {"status":"stat_loadout_candidate","budget_gp":200,"total_cost_gp":100,"selected_items":[
            {"item_id":1,"item_name":"Helm","slot":"head","cost":100,"objective_value":5,"eligibility_status":"candidate_with_unknown_restrictions","reasons":["Quest/unlock restrictions are not verified"]}
        ]}
    def test_consistent_uncertain_candidate_passes(self):
        self.assertEqual(audit(self.shortlist,self.loadout)["status"],"passed")
    def test_duplicate_item_in_slot_is_error(self):
        data={"results_by_slot":{"head":[self.shortlist["results_by_slot"]["head"][0],self.shortlist["results_by_slot"]["head"][0]]}}
        result=audit(data,None)
        self.assertIn("duplicate_item_in_slot",[x["code"] for x in result["errors"]])
    def test_overstated_certainty_is_error(self):
        data={"results_by_slot":{"head":[dict(self.shortlist["results_by_slot"]["head"][0],status="confirmed_usable")]}}
        result=audit(data,None)
        self.assertIn("unsupported_certainty_status",[x["code"] for x in result["errors"]])
    def test_unknown_cost_cannot_be_selectable(self):
        data={"results_by_slot":{"head":[dict(self.shortlist["results_by_slot"]["head"][0],cost=None)]}}
        result=audit(data,None)
        self.assertIn("selectable_without_cost",[x["code"] for x in result["errors"]])
    def test_budget_overrun_and_cost_mismatch_are_errors(self):
        loadout=dict(self.loadout,budget_gp=50,total_cost_gp=101)
        result=audit(self.shortlist,loadout)
        codes=[x["code"] for x in result["errors"]]
        self.assertIn("budget_overrun",codes)
        self.assertIn("total_cost_mismatch",codes)
    def test_duplicate_selected_slot_is_error(self):
        loadout=dict(self.loadout,selected_items=self.loadout["selected_items"]*2,total_cost_gp=200)
        result=audit(self.shortlist,loadout)
        self.assertIn("duplicate_selected_slot",[x["code"] for x in result["errors"]])
    def test_ineligible_selection_is_error(self):
        loadout=dict(self.loadout,selected_items=[dict(self.loadout["selected_items"][0],eligibility_status="ineligible_by_known_skill_requirement")])
        result=audit(self.shortlist,loadout)
        self.assertIn("unsafe_selected_status",[x["code"] for x in result["errors"]])

if __name__=="__main__":
    unittest.main()
