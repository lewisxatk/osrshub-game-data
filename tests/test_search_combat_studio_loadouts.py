import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from search_combat_studio_loadouts import search_loadouts

def eq(i,n,s,a,st,spd=None):
 return {"id":i,"name":n,"slot":s,"bonuses":{"attack_stab":a,"attack_slash":a,"attack_crush":a,"melee_strength":st},"attack_speed":spd,"source_urls":["https://example.test/item"]}
def prof(i,n,s,a,st,spd=None):
 return {"id":i,"name":n,"slot":s,"bonuses":{"attack_stab":a,"attack_slash":a,"attack_crush":a,"melee_strength":st},"attack_speed":spd,"skill_requirements":[],"source_urls":["https://example.test/item"],"data_status":"joined_fields_present"}
class DPSSearchTests(unittest.TestCase):
 def setUp(self):
  self.eq=[eq(1,"Slow sword","weapon",50,40,6),eq(2,"Fast sword","weapon",40,35,4),eq(3,"Good helm","head",10,5),eq(4,"Quest helm","head",100,50)]
  self.req=[{"item_id":i,"requirements_status":"known_empty","requirements":[]} for i in (1,2,3,4)]
  self.unlock=[{"item_id":i,"requirements_status":"known_empty","required_quests":[]} for i in (1,2,3)]+[{"item_id":4,"requirements_status":"known","required_quests":["Locked Quest"]}]
  self.profiles=[prof(1,"Slow sword","weapon",50,40,6),prof(2,"Fast sword","weapon",40,35,4),prof(3,"Good helm","head",10,5),prof(4,"Quest helm","head",100,50)]
  self.account={"skills":{"Attack":99,"Strength":99,"Defence":99},"completed_quests":[],"current_equipment":{"weapon":1}}
  self.cost={"1":1000,"2":2000,"3":500,"4":1}; self.inputs={"effective_attack":120,"effective_strength":120,"effective_defence":80,"defence_bonus":80}
 def run_search(self,budget=4000,**kw):
  return search_loadouts(self.eq,self.req,self.unlock,self.profiles,self.account,self.cost,budget,self.inputs,"slash",**kw)
 def test_ranks_complete_loadouts_by_dps(self):
  r=self.run_search(); self.assertIn(r["status"],("dps_ranked_candidates","search_truncated")); self.assertIsNotNone(r["best_loadout"])
  self.assertGreater(r["best_loadout"]["combat_result"]["dps"],0); self.assertEqual(r["best_loadout"]["weapon"]["item_id"],2)
  self.assertLessEqual(r["best_loadout"]["total_cost_gp"],4000)
 def test_quest_locked_item_not_selected(self):
  r=self.run_search(); self.assertNotIn(4,[x["item_id"] for x in r["best_loadout"]["selected_items"]])
  self.assertEqual(next(x for x in r["eligibility_audit"] if x["item_id"]==4)["status"],"ineligible")
 def test_missing_requirements_withhold_item(self):
  req=[x for x in self.req if x["item_id"]!=3]
  r=search_loadouts(self.eq,req,self.unlock,self.profiles,self.account,self.cost,4000,self.inputs)
  self.assertNotIn(3,[x["item_id"] for x in r["best_loadout"]["selected_items"]])
 def test_budget_enforced(self):
  r=self.run_search(budget=100); self.assertTrue(r["best_loadout"] is None or r["best_loadout"]["total_cost_gp"]<=100)
 def test_node_limit_reported(self):
  r=self.run_search(node_limit=1); self.assertTrue(r["search"]["truncated"]); self.assertEqual(r["status"],"search_truncated")
 def test_duplicate_profile_ids_rejected(self):
  with self.assertRaisesRegex(ValueError,"duplicate combat profile ID"):
   search_loadouts(self.eq,self.req,self.unlock,self.profiles+[self.profiles[0]],self.account,self.cost,4000,self.inputs)
 def test_invalid_style_rejected(self):
  with self.assertRaises(ValueError): search_loadouts(self.eq,self.req,self.unlock,self.profiles,self.account,self.cost,4000,self.inputs,"magic")
if __name__=="__main__": unittest.main()
