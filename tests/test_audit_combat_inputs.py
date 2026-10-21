"""Tests for input validation ahead of combat comparisons."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from audit_combat_inputs import audit_inputs
class CombatInputAuditTests(unittest.TestCase):
    def setUp(self):
        self.profile={"skills":{"Attack":80,"Strength":86,"Defence":80,"Ranged":93,"Magic":84,"Hitpoints":90,"Prayer":70},"excluded_item_ids":[4151],"excluded_item_names":[],"source_url":"https://example.org/profile"}
        self.costs={"4151":1200000,"11802":50000000}
        self.inputs={"effective_attack":100,"effective_strength":110,"effective_defence":90,"defence_bonus":120,"source_url":"https://oldschool.runescape.wiki/","checked_on":"2026-10-21"}
    def test_valid_complete_inputs_pass(self):
        result=audit_inputs(self.profile,self.costs,self.inputs,100000000)
        self.assertEqual(result["status"],"passed")
        self.assertEqual(result["cost_entry_count"],2)
    def test_missing_provenance_warns_without_claiming_facts_valid(self):
        inputs=dict(self.inputs); inputs.pop("source_url"); inputs.pop("checked_on")
        result=audit_inputs(self.profile,self.costs,inputs,100000000)
        self.assertEqual(result["status"],"passed_with_warnings")
        self.assertTrue(any("source URL" in warning for warning in result["warnings"]))
    def test_invalid_levels_and_costs_fail(self):
        profile=dict(self.profile,skills={"Attack":True,"Strength":120})
        result=audit_inputs(profile,{"4151":-1},self.inputs,100)
        self.assertEqual(result["status"],"failed")
        self.assertTrue(result["errors"])
    def test_invalid_exclusion_shape_fails(self):
        result=audit_inputs(dict(self.profile,excluded_item_ids=["4151"]),self.costs,self.inputs,100)
        self.assertEqual(result["status"],"failed")
    def test_missing_skills_warns_not_infers(self):
        result=audit_inputs({"skills":{"Attack":80}},self.costs,self.inputs,100)
        self.assertTrue(any("omits skill levels" in warning for warning in result["warnings"]))
    def test_invalid_budget_fails(self):
        self.assertEqual(audit_inputs(self.profile,self.costs,self.inputs,-1)["status"],"failed")
if __name__=="__main__":unittest.main()
