"""Tests for budget-constrained multi-slot stat loadout selection."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from optimize_equipment_loadout import optimize_loadout
class LoadoutOptimizerTests(unittest.TestCase):
    def setUp(self):
        self.shortlist={"objective":"melee_strength","objective_field":"bonuses.melee_strength","results_by_slot":{
          "head":[{"item_id":1,"item_name":"Cheap helm","status":"candidate_with_unknown_restrictions","cost":20,"objective_value":2,"reasons":[]},{"item_id":2,"item_name":"Strong helm","status":"candidate_with_unknown_restrictions","cost":60,"objective_value":8,"reasons":[]}],
          "body":[{"item_id":3,"item_name":"Body","status":"candidate_with_unknown_restrictions","cost":50,"objective_value":7,"reasons":[]}],
          "legs":[{"item_id":4,"item_name":"Unknown cost","status":"candidate_with_unknown_restrictions","cost":None,"objective_value":10,"reasons":[]}],
          "weapon":[{"item_id":5,"item_name":"Ineligible","status":"ineligible_by_known_skill_requirement","cost":1,"objective_value":100,"reasons":[]}]}}
    def test_selects_best_combination_within_total_budget(self):
        result=optimize_loadout(self.shortlist,100)
        self.assertEqual(result["total_cost_gp"],70)
        self.assertEqual({x["item_id"] for x in result["selected_items"]},{1,3})
        self.assertEqual(result["objective_total"],9)
    def test_does_not_select_ineligible_or_unknown_cost_items(self):
        result=optimize_loadout(self.shortlist,100); ids={x["item_id"] for x in result["selected_items"]}
        self.assertNotIn(4,ids); self.assertNotIn(5,ids)
    def test_budget_can_leave_slots_empty(self):
        result=optimize_loadout(self.shortlist,10); self.assertEqual(result["selected_items"],[]); self.assertEqual(result["total_cost_gp"],0)
    def test_search_limit_is_explicit(self):
        result=optimize_loadout(self.shortlist,100,node_limit=1); self.assertEqual(result["status"],"search_truncated"); self.assertLessEqual(result["search_nodes"],1)
    def test_invalid_arguments_fail(self):
        with self.assertRaises(ValueError): optimize_loadout({},-1)
        with self.assertRaises(ValueError): optimize_loadout(self.shortlist,100,top_per_slot=0)
if __name__=="__main__":unittest.main()
