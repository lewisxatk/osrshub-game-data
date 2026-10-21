import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from evaluate_ranged_loadout import evaluate_ranged_loadout
def item(i,n,slot,a,s,speed=None): return {"id":i,"name":n,"slot":slot,"bonuses":{"attack_ranged":a,"ranged_strength":s},"attack_speed":speed,"skill_requirements":[],"data_status":"joined_fields_present","source_urls":["https://example.test"]}
class RangedTests(unittest.TestCase):
 def setUp(self):
  self.rows=[item(1,"Test bow","weapon",80,70,4),item(2,"Coif","head",10,2)]
  self.costs={"1":1000,"2":200}; self.inputs={"effective_ranged":90,"effective_defence":80,"defence_bonus":80}
 def test_calculates_baseline(self):
  r=evaluate_ranged_loadout(self.rows,[1,2],self.costs,2000,self.inputs)
  self.assertEqual(r["total_cost_gp"],1200); self.assertEqual(r["aggregated_bonuses"]["ranged_strength"],72); self.assertGreater(r["combat_result"]["dps"],0)
 def test_budget_overrun(self):
  with self.assertRaisesRegex(ValueError,"exceeding budget"): evaluate_ranged_loadout(self.rows,[1,2],self.costs,1000,self.inputs)
 def test_missing_bonus_not_zero(self):
  with self.assertRaisesRegex(ValueError,"unknown ranged attack"): evaluate_ranged_loadout([item(1,"Bow","weapon",None,70,4)],[1],self.costs,2000,self.inputs)
 def test_requires_weapon(self):
  with self.assertRaisesRegex(ValueError,"exactly one"): evaluate_ranged_loadout(self.rows,[2],self.costs,2000,self.inputs)
 def test_duplicate_slot(self):
  with self.assertRaisesRegex(ValueError,"multiple selected items"): evaluate_ranged_loadout(self.rows+[item(3,"Another coif","head",1,1)],[1,2,3],{**self.costs,"3":1},3000,self.inputs)
if __name__=="__main__": unittest.main()
