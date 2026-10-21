"""Tests for caller-selected melee loadout baseline evaluation."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from evaluate_combat_loadout import evaluate_loadout

def item(rid, name, slot, attack, strength, speed=None):
    return {"id":rid,"name":name,"slot":slot,
      "bonuses":{"attack_stab":attack,"attack_slash":attack,"attack_crush":attack,"melee_strength":strength},
      "attack_speed":speed,"skill_requirements":[],"source_urls":["https://example.test/item"],
      "data_status":"joined_fields_present"}
class EvaluateCombatLoadoutTests(unittest.TestCase):
    def setUp(self):
        self.rows=[item(1,"Test sword","weapon",80,70,4),item(2,"Test helm","head",5,2),item(3,"Test body","body",10,5)]
        self.costs={"1":1000,"2":500,"3":1500}
        self.inputs={"effective_attack":100,"effective_strength":100,"effective_defence":80,"defence_bonus":80}
    def test_aggregates_stats_and_returns_baseline_dps(self):
        result=evaluate_loadout(self.rows,[1,2,3],self.costs,4000,self.inputs,"slash")
        self.assertEqual(result["total_cost_gp"],3000)
        self.assertEqual(result["remaining_budget_gp"],1000)
        self.assertEqual(result["aggregated_bonuses"]["attack_style_bonus"],95)
        self.assertEqual(result["aggregated_bonuses"]["melee_strength"],77)
        self.assertGreater(result["combat_result"]["dps"],0)
        self.assertEqual(result["status"],"baseline_loadout_estimate_with_limitations")
    def test_budget_overrun_rejected(self):
        with self.assertRaisesRegex(ValueError,"exceeding budget"):
            evaluate_loadout(self.rows,[1,2,3],self.costs,2000,self.inputs,"slash")
    def test_requires_exactly_one_weapon(self):
        with self.assertRaisesRegex(ValueError,"exactly one"):
            evaluate_loadout(self.rows,[2,3],self.costs,4000,self.inputs,"slash")
    def test_duplicate_slots_rejected(self):
        rows=self.rows+[item(4,"Second helm","head",1,1)]
        with self.assertRaisesRegex(ValueError,"multiple selected items"):
            evaluate_loadout(rows,[1,2,4],{**self.costs,"4":1},5000,self.inputs,"slash")
    def test_missing_bonus_not_silently_zeroed(self):
        rows=[dict(self.rows[0],bonuses={"attack_slash":None,"melee_strength":70})]
        with self.assertRaisesRegex(ValueError,"unknown or non-integer"):
            evaluate_loadout(rows,[1],self.costs,4000,self.inputs,"slash")
    def test_duplicate_ids_rejected(self):
        with self.assertRaisesRegex(ValueError,"duplicate IDs"):
            evaluate_loadout(self.rows,[1,1],self.costs,4000,self.inputs,"slash")
    def test_invalid_style_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_loadout(self.rows,[1],self.costs,4000,self.inputs,"ranged")
if __name__=="__main__": unittest.main()
