import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from compare_loadout_reports import compare_reports
def r(d,c,s="slash",speed=4): return {"status":"baseline_only","attack_style":s,"combat_result":{"dps":d},"total_cost_gp":c,"weapon":{"attack_speed_ticks":speed},"selected_items":[]}
class CompareTests(unittest.TestCase):
 def test_delta(self):
  x=compare_reports(r(2,100),r(3,150)); self.assertEqual(x["delta"]["dps_percent"],50); self.assertEqual(x["delta"]["additional_gp_per_dps"],50)
 def test_cheaper_lower_dps(self):
  x=compare_reports(r(3,200),r(2,100)); self.assertTrue(x["delta"]["cheaper"]); self.assertFalse(x["delta"]["improved_baseline_dps"])
 def test_zero_dps(self): self.assertIsNone(compare_reports(r(0,100),r(1,150))["delta"]["dps_percent"])
 def test_style_mismatch(self): self.assertFalse(compare_reports(r(1,100),r(2,200,"crush"))["comparability"]["same_attack_style"])
 def test_missing_values(self):
  with self.assertRaises(ValueError): compare_reports({},r(1,100))
if __name__=="__main__": unittest.main()
